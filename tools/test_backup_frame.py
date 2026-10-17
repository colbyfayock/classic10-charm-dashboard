import gzip
import hashlib
import io
import os
from pathlib import Path
import struct
import tempfile
import unittest

from backup_frame import encoded_lines, encoded_pipeline, receive_encoded, receive_stream, verify_gzip


class FragmentedStream:
    def __init__(self, data):
        self.data = io.BytesIO(data)

    def recv(self, count):
        return self.data.read(min(count, 3))


def packet(kind, data=b""):
    return kind + struct.pack("<I", len(data)) + data


class BackupFrameTest(unittest.TestCase):
    def test_encoded_pipe_reads_lines_and_last_fragment(self):
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"first\r\nlast")
        os.close(write_fd)
        with os.fdopen(read_fd, "rb") as pipe:
            self.assertEqual(list(encoded_lines(pipe)), [b"first\r", b"last"])

    def test_encoded_pipe_times_out_instead_of_hanging(self):
        read_fd, write_fd = os.pipe()
        try:
            with os.fdopen(read_fd, "rb") as pipe:
                with self.assertRaises(TimeoutError):
                    list(encoded_lines(pipe, idle_timeout=0.01))
        finally:
            os.close(write_fd)

    def test_range_pipeline_bounds_offsets_and_uses_read_only_commands(self):
        pipeline = encoded_pipeline("/dev/block/mmcblk0", 67108864, 67108864)
        self.assertIn("skip=1024 count=1024", pipeline)
        self.assertIn("set -o pipefail", pipeline)
        self.assertNotIn("of=", pipeline)
        for source, size, offset in (
            ("/dev/block/unknown", 65536, 0),
            ("/dev/block/mmcblk0", 65536, -65536),
            ("/dev/block/mmcblk0", 1, 0),
            ("/dev/block/mmcblk0boot0", 4194304, 65536),
        ):
            with self.assertRaises(ValueError):
                encoded_pipeline(source, size, offset)

    def encoded_lines(self, data):
        compressed = gzip.compress(data)
        return [compressed[i:i + 1024].hex().encode() + b"\r\n" for i in range(0, len(compressed), 1024)]

    def test_decodes_compressed_text_and_hashes_raw_bytes(self):
        data = bytes(range(256)) * 3000
        sink = io.BytesIO()
        lines = self.encoded_lines(data) + [b"CAPTURE_STATUS:0\r\n"]
        digest = receive_encoded(lines, sink, len(data))
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        self.assertEqual(gzip.decompress(sink.getvalue()), data)

    def test_encoded_capture_requires_success_marker_and_exact_size(self):
        data = b"example"
        for lines, expected in (
            (self.encoded_lines(data), len(data)),
            (self.encoded_lines(data) + [b"CAPTURE_STATUS:1\n"], len(data)),
            (self.encoded_lines(data) + [b"CAPTURE_STATUS:0\n"], len(data) + 1),
            (self.encoded_lines(data) + [b"CAPTURE_STATUS:0\n"], len(data) - 1),
            ([b"not hexadecimal\n", b"CAPTURE_STATUS:0\n"], len(data)),
        ):
            with self.assertRaises(ValueError):
                receive_encoded(lines, io.BytesIO(), expected)

    def test_encoded_capture_rejects_truncation_and_trailing_data(self):
        for compressed in (gzip.compress(b"abc")[:-2], gzip.compress(b"abc") + b"extra"):
            with self.assertRaises(ValueError):
                receive_encoded([compressed.hex().encode(), b"CAPTURE_STATUS:0"], io.BytesIO(), 3)

    def test_receives_fragmented_binary_data_and_hashes_it(self):
        data = bytes(range(256)) * 4
        stream = FragmentedStream(packet(b"DATA", data) + packet(b"DONE"))
        sink = io.BytesIO()
        digest = receive_stream(stream, sink, len(data))
        self.assertEqual(sink.getvalue(), data)
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())

    def test_rejects_short_oversized_or_truncated_stream(self):
        for wire, expected in (
            (packet(b"DATA", b"abc") + packet(b"DONE"), 4),
            (packet(b"DATA", b"abc") + packet(b"DONE"), 2),
            (b"DATA" + struct.pack("<I", 3) + b"a", 3),
        ):
            with self.assertRaises(ValueError):
                receive_stream(FragmentedStream(wire), io.BytesIO(), expected)

    def test_rejects_sync_error_without_disclosing_device_message(self):
        with self.assertRaisesRegex(ValueError, "device rejected") as caught:
            receive_stream(FragmentedStream(packet(b"FAIL", b"private diagnostic")), io.BytesIO(), 1)
        self.assertNotIn("private diagnostic", str(caught.exception))

    def test_rejects_invalid_or_oversized_packet(self):
        for wire in (packet(b"NOPE"), b"DATA" + struct.pack("<I", 65537)):
            with self.assertRaises(ValueError):
                receive_stream(FragmentedStream(wire), io.BytesIO(), 100000)

    def test_verifies_compressed_readback(self):
        data = bytes(range(256)) * 300
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.gz"
            path.write_bytes(gzip.compress(data))
            verify_gzip(path, len(data), hashlib.sha256(data).hexdigest())
            with self.assertRaises(ValueError):
                verify_gzip(path, len(data) + 1, hashlib.sha256(data).hexdigest())
            with self.assertRaises(ValueError):
                verify_gzip(path, len(data), "incorrect digest")

    def test_rejects_filler_and_corrupt_gzip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.gz"
            data = bytes([204]) * 65536
            path.write_bytes(gzip.compress(data))
            with self.assertRaisesRegex(ValueError, "filler"):
                verify_gzip(path, len(data), hashlib.sha256(data).hexdigest())
            path.write_bytes(b"not a gzip stream")
            with self.assertRaises((OSError, EOFError)):
                verify_gzip(path, 1, "incorrect digest")


if __name__ == "__main__":
    unittest.main()
