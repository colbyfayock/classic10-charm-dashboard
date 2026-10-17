import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "android/navigation"
ANDROID = "{http://schemas.android.com/apk/res/android}"


class NavigationHelperTest(unittest.TestCase):
    def test_policy_with_real_java(self):
        java_home = os.environ.get("JAVA_HOME")
        javac = str(Path(java_home) / "bin/javac") if java_home else shutil.which("javac")
        java = str(Path(java_home) / "bin/java") if java_home else shutil.which("java")
        if not javac or not java:
            self.skipTest("A JDK is required for navigation policy tests")
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([
                javac, "-d", directory,
                str(SOURCE / "src/com/colbyfayock/framecontrols/ControlPolicy.java"),
                str(SOURCE / "test/ControlPolicyTest.java"),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([java, "-cp", directory, "com.colbyfayock.framecontrols.ControlPolicyTest"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_manifest_has_only_necessary_privileges_and_no_home_or_boot(self):
        root = ET.parse(SOURCE / "AndroidManifest.xml").getroot()
        self.assertEqual(root.find("uses-sdk").get(ANDROID + "minSdkVersion"), "19")
        self.assertEqual({node.get(ANDROID + "name") for node in root.findall("uses-permission")}, {"android.permission.SYSTEM_ALERT_WINDOW"})
        self.assertFalse(root.findall(".//receiver"))
        self.assertFalse(any(node.get(ANDROID + "name") == "android.intent.category.HOME" for node in root.findall(".//category")))
        service = root.find("application/service")
        self.assertEqual(service.get(ANDROID + "permission"), "android.permission.BIND_ACCESSIBILITY_SERVICE")
        self.assertEqual(root.find("application").get(ANDROID + "allowBackup"), "false")

    def test_accessibility_has_no_event_subscription_or_screen_access(self):
        root = ET.parse(SOURCE / "res/xml/navigation_service.xml").getroot()
        self.assertEqual(root.get(ANDROID + "canRetrieveWindowContent"), "false")
        self.assertEqual(root.get(ANDROID + "accessibilityEventTypes", "0"), "0")
        self.assertEqual(root.get(ANDROID + "accessibilityFlags", "0"), "0")
        text = (SOURCE / "src/com/colbyfayock/framecontrols/NavigationService.java").read_text()
        for forbidden in ("getRootInActiveWindow", "Settings.Secure", "Runtime.getRuntime", "getWindows("):
            self.assertNotIn(forbidden, text)
        self.assertIn("eventTypes = 0", text)


if __name__ == "__main__":
    unittest.main()
