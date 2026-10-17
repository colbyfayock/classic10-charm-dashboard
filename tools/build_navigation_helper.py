#!/usr/bin/env python3
"""Build and inspect Frame Controls on macOS. Never contacts or changes a frame."""

import datetime
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import secrets
import stat
import subprocess
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "android/navigation"


def private_dir(path):
    if path.is_symlink():
        raise ValueError("Refusing a symlinked private directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir() or stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise ValueError("Private build directories must have mode 0700")


def verify_archive(data, pin):
    if (len(data) != pin["size"] or hashlib.sha1(data).hexdigest() != pin["sha1"]
            or hashlib.sha256(data).hexdigest() != pin["sha256"]):
        raise ValueError("STOP: SDK size or checksum pin mismatch")


def extract_verified(data, archive_root, target):
    """Extract only bounded regular files under the pinned single archive root."""
    if target.is_symlink() or not target.is_dir():
        raise ValueError("SDK extraction target must be a real directory")
    target = target.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if sum(item.file_size for item in archive.infolist()) > 2 * 1024 ** 3:
            raise ValueError("SDK archive expanded size exceeds limit")
        for item in archive.infolist():
            name = PurePosixPath(item.filename)
            if (name.is_absolute() or ".." in name.parts or not name.parts
                    or name.parts[0] != archive_root or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError("Unsafe SDK archive path or symlink")
        for item in archive.infolist():
            parts = PurePosixPath(item.filename).parts[1:]
            if not parts:
                continue
            destination = target.joinpath(*parts)
            if any(path.is_symlink() for path in [destination, *destination.parents]):
                raise ValueError("Refusing symlinked SDK output path")
            if item.is_dir():
                private_dir(destination)
                continue
            private_dir(destination.parent)
            content = archive.read(item)
            if destination.exists():
                if destination.read_bytes() != content:
                    raise ValueError("STOP: existing SDK file differs from pinned archive")
            else:
                with destination.open("xb") as output:
                    output.write(content)
            executable = bool((item.external_attr >> 16) & 0o100)
            destination.chmod(0o700 if executable else 0o600)


def run(arguments, label):
    print(label, flush=True)
    result = subprocess.run([str(value) for value in arguments], capture_output=True, text=True)
    if result.returncode:
        # Arguments contain paths, never a keystore passphrase.
        print(result.stdout)
        print(result.stderr)
        raise ValueError("Host build command failed: " + label)
    return result.stdout


def main():
    if platform.system() != "Darwin":
        raise ValueError("Pinned native build-tools are for macOS only")
    os.umask(0o077)
    base = ROOT / "backups"
    private_dir(base)
    if subprocess.run(["git", "check-ignore", "--quiet", "backups/navigation-builds/inspection.json"], cwd=ROOT).returncode:
        raise ValueError("Private build output must be Git-ignored")
    if subprocess.check_output(["git", "ls-files", "backups"], cwd=ROOT).strip():
        raise ValueError("STOP: private artifacts are tracked")
    lock_path = base / ".navigation-build.lock"
    if lock_path.is_symlink():
        raise ValueError("Refusing symlinked build lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        build(base)


def build(base):
    java_home = Path(os.environ.get("JAVA_HOME") or subprocess.check_output(
        ["/usr/libexec/java_home", "-v", "17"], text=True).strip())
    downloads = base / "android-toolchain-downloads"
    sdk = base / "android-sdk"
    private_dir(downloads)
    private_dir(sdk)
    pins = json.loads((SOURCE / "toolchain.json").read_text())
    for pin in pins["archives"]:
        if not pin["url"].startswith("https://dl.google.com/android/repository/"):
            raise ValueError("SDK URL must use the pinned official origin")
        archive = downloads / pin["file"]
        if archive.is_symlink():
            raise ValueError("Refusing symlinked SDK archive")
        if archive.exists():
            if archive.stat().st_size != pin["size"]:
                raise ValueError("STOP: cached SDK archive size mismatch")
            data = archive.read_bytes()
        else:
            data = subprocess.check_output([
                "curl", "--fail", "--location", "--silent", "--show-error",
                "--proto", "=https", "--max-time", "180", pin["url"],
            ])
        verify_archive(data, pin)
        if not archive.exists():
            with archive.open("xb") as output:
                output.write(data)
        target = sdk / pin["destination"]
        if target.is_symlink():
            raise ValueError("Refusing symlinked SDK destination")
        private_dir(target)
        extract_verified(data, pin["archive_root"], target)
        print(pin["name"] + " archive and installed contents verified.", flush=True)

    tools = sdk / "build-tools/34.0.0"
    android_jar = sdk / "platforms/android-19/android.jar"
    builds = base / "navigation-builds"
    private_dir(builds)
    folder = builds / (datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])
    private_dir(folder)
    generated, classes, dex = folder / "generated", folder / "classes", folder / "dex"
    for path in (generated, classes, dex):
        private_dir(path)
    resources, unsigned, aligned = folder / "resources.zip", folder / "unsigned.apk", folder / "aligned.apk"
    run([tools / "aapt2", "compile", "--dir", SOURCE / "res", "-o", resources], "Compile resources against pinned tools")
    run([tools / "aapt2", "link", "-I", android_jar, "--manifest", SOURCE / "AndroidManifest.xml",
         "--java", generated, "-o", unsigned, resources], "Link manifest using the API 19 platform")
    sources = sorted((SOURCE / "src").rglob("*.java")) + sorted(generated.rglob("*.java"))
    run([java_home / "bin/javac", "-source", "8", "-target", "8", "-Xlint:-options",
         "-bootclasspath", android_jar, "-d", classes, *sources], "Compile Java against API 19 only")
    run([java_home / "bin/java", "-cp", tools / "lib/d8.jar", "com.android.tools.r8.D8",
         "--release", "--min-api", "19", "--lib", android_jar, "--output", dex,
         *sorted(classes.rglob("*.class"))], "Produce API 19 DEX")
    with zipfile.ZipFile(unsigned, "a") as archive:
        archive.write(dex / "classes.dex", "classes.dex")
    run([tools / "zipalign", "-f", "4", unsigned, aligned], "Align APK")

    signing = base / "navigation-signing"
    private_dir(signing)
    keystore, passphrase = signing / "frame-controls.p12", signing / "keystore-passphrase"
    if keystore.is_symlink() or passphrase.is_symlink():
        raise ValueError("Refusing symlinked signing material")
    if not keystore.exists() and not passphrase.exists():
        with passphrase.open("x") as output:
            output.write(secrets.token_urlsafe(48) + "\n")
        run([java_home / "bin/keytool", "-genkeypair", "-storetype", "PKCS12", "-keystore", keystore,
             "-storepass:file", passphrase, "-alias", "framecontrols", "-keyalg", "RSA", "-keysize", "3072",
             "-validity", "3650", "-dname", "CN=Frame Controls Local Development"], "Generate private local signing key")
    elif not keystore.is_file() or not passphrase.is_file():
        raise ValueError("Incomplete signing material; refusing to replace it")
    if any(stat.S_IMODE(path.stat().st_mode) != 0o600 for path in (keystore, passphrase)):
        raise ValueError("Signing files must be owner-only")
    apk = folder / "frame-controls.apk"
    # Use the pinned official signer CLI; credentials are passed by file, not argv.
    signer = [java_home / "bin/java", "-jar", tools / "lib/apksigner.jar"]
    run([*signer, "sign", "--ks", keystore, "--ks-pass", "file:" + str(passphrase),
         "--ks-key-alias", "framecontrols", "--min-sdk-version", "19",
         "--v1-signing-enabled", "true", "--v2-signing-enabled", "true",
         "--v3-signing-enabled", "false", "--v4-signing-enabled", "false",
         "--out", apk, aligned], "Sign without exposing the private passphrase")
    verification = run([*signer, "verify", "--verbose", "--print-certs", "--min-sdk-version", "19",
                        "--max-sdk-version", "19", apk], "Verify signing for API 19")
    if "Verified using v1 scheme (JAR signing): true" not in verification:
        raise ValueError("APK must have valid API-19-compatible v1 signing")
    badging = run([tools / "aapt2", "dump", "badging", apk], "Inspect actual APK SDK/package/permissions")
    permissions = re.findall(r"uses-permission: name='([^']+)'", badging)
    if ("name='com.colbyfayock.framecontrols'" not in badging
            or "sdkVersion:'19'" not in badging or "targetSdkVersion:'19'" not in badging
            or permissions != ["android.permission.SYSTEM_ALERT_WINDOW"]):
        raise ValueError("Unexpected actual APK identity, SDK, or permissions")
    manifest = run([tools / "aapt2", "dump", "xmltree", "--file", "AndroidManifest.xml", apk], "Inspect packaged manifest")
    service = run([tools / "aapt2", "dump", "xmltree", "--file", "res/xml/navigation_service.xml", apk], "Inspect packaged accessibility configuration")
    certificate = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})", verification)
    if not certificate:
        raise ValueError("Missing signing-certificate inspection result")
    for name, content in (("signature.txt", verification), ("badging.txt", badging),
                          ("manifest.txt", manifest), ("accessibility.txt", service)):
        (folder / name).write_text(content)
    report = {
        "built_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "package": "com.colbyfayock.framecontrols", "version": "0.1.0",
        "min_api": 19, "target_api": 19, "permissions": permissions,
        "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "certificate_sha256": certificate.group(1), "apk_bytes": apk.stat().st_size,
        "v1_signature_verified_for_api_19": True,
        "installed_on_frame": False, "physical_navigation_tested": False,
        "source_hashes": {str(path.relative_to(SOURCE)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(SOURCE.rglob("*")) if path.is_file()},
    }
    (folder / "inspection.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Host build and API-19 signature/manifest inspection passed. Nothing installed.", flush=True)
    print("Build directory: " + str(folder.relative_to(ROOT)), flush=True)
    print("APK SHA-256: " + report["apk_sha256"], flush=True)
    print("Certificate SHA-256: " + report["certificate_sha256"], flush=True)


if __name__ == "__main__":
    main()
