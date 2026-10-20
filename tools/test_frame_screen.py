from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from frame_screen import cleanup, decode_capture, store_capture


def png_chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)


def example_png():
    return b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + png_chunk(b'IDAT', zlib.compress(bytes(4))) + png_chunk(b'IEND', b'')


class FrameScreenTest(unittest.TestCase):
    def test_decodes_successful_capture_and_checks_crc(self):
        data = example_png()
        self.assertEqual(decode_capture(data.hex() + '\r\nSCREEN_STATUS:0\r\n'), data)
        corrupt = bytearray(data)
        corrupt[25] ^= 1
        with self.assertRaises(ValueError):
            decode_capture(bytes(corrupt).hex() + '\nSCREEN_STATUS:0')

    def test_rejects_failed_or_truncated_capture(self):
        for output in ('abcd\nSCREEN_STATUS:1', 'not hex\nSCREEN_STATUS:0', example_png()[:-1].hex() + '\nSCREEN_STATUS:0'):
            with self.assertRaises(ValueError):
                decode_capture(output)

    def test_cleanup_removes_only_owned_image_and_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            (folder / 'unrelated.txt').write_text('leave this alone')
            store_capture(folder, example_png())
            cleanup(folder)
            self.assertEqual([p.name for p in folder.iterdir()], ['unrelated.txt'])

    def test_refuses_unknown_or_changed_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            (folder / 'current.png').write_bytes(example_png())
            with self.assertRaises(ValueError):
                cleanup(folder)
            (folder / 'current.png').unlink()
            store_capture(folder, example_png())
            (folder / 'current.png').write_bytes(b'changed file')
            with self.assertRaises(ValueError):
                cleanup(folder)
            self.assertEqual((folder / 'current.png').read_bytes(), b'changed file')

    def test_refuses_overwrite_and_symlink_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            store_capture(folder, example_png())
            with self.assertRaises(ValueError):
                store_capture(folder, example_png())
            cleanup(folder)
            target = folder / 'unrelated.png'
            target.write_bytes(example_png())
            (folder / 'current.png').symlink_to(target)
            with self.assertRaises(ValueError):
                cleanup(folder)
            self.assertEqual(target.read_bytes(), example_png())


if __name__ == '__main__':
    unittest.main()
