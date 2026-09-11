"""Reference integrity and local output isolation checks; no network needed."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import fetch_reference_inputs as fetch
import build_paths


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.data = b"verified reference"
        self.entry = dict(path="part.step", url="https://www.pololu.com/reference.step",
                          bytes=len(self.data), sha256=hashlib.sha256(self.data).hexdigest())

    def tearDown(self):
        self.temporary.cleanup()

    def test_existing_file_verifies_without_network(self):
        (self.root / "part.step").write_bytes(self.data)
        with patch.object(fetch, "urlopen", side_effect=AssertionError("unexpected network")):
            self.assertEqual(fetch.fetch_one(self.entry, self.root, True), "verified")

    def test_wrong_existing_file_is_never_replaced(self):
        path = self.root / "part.step"
        path.write_bytes(b"different model")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            fetch.fetch_one(self.entry, self.root)
        self.assertEqual(path.read_bytes(), b"different model")

    def test_wrong_download_is_not_installed(self):
        response = io.BytesIO(b"wrong model")
        response.url = self.entry["url"]
        with patch.object(fetch, "urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "mismatch"):
                fetch.fetch_one(self.entry, self.root)
        self.assertFalse((self.root / "part.step").exists())

    def test_reference_path_cannot_escape_cache(self):
        with self.assertRaisesRegex(ValueError, "escapes cache"):
            fetch.destination({**self.entry, "path": "../outside.step"}, self.root)

    def test_build_root_cannot_replace_public_cad(self):
        for path in (ROOT, ROOT / "cad", ROOT / "src"):
            with patch.dict("os.environ", {"MICRODUCKLING_BUILD_ROOT": str(path)}):
                with self.assertRaises(ValueError):
                    build_paths.build_root()


if __name__ == "__main__":
    unittest.main()
