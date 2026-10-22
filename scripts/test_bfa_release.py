import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bfa_release", ROOT / "scripts/bfa_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
VERSION = "0.3.0-beta.7-bfa"
SHA = "a" * 40


class ReleaseContractTests(unittest.TestCase):
    def test_normalizes_version(self):
        self.assertEqual(release.validate("v" + VERSION, SHA), (VERSION, SHA))

    def test_rejects_mutable_or_malformed_source(self):
        for value in ("dev", "release/bfa", "a" * 7, "A" * 40, SHA + "\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.validate(VERSION, value)

    def test_rejects_non_bfa_and_unsafe_versions(self):
        for value in ("0.3.0", "0.3.0-beta.7", "../0.3.0-bfa", VERSION + "\n", "$(touch /tmp/injected)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.validate(value, SHA)

    def test_metadata_rejects_wrong_checkout(self):
        with patch.dict(os.environ, RELEASE_VERSION=VERSION, SOURCE_SHA=SHA), \
             patch.object(release, "git_sha", return_value="b" * 40), \
             patch.object(sys, "argv", ["bfa_release.py", "metadata", "android", "unused.json"]):
            with self.assertRaisesRegex(ValueError, "differs"):
                release.main()

    def test_checksums_cover_assets_and_detect_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            (path / "package.zip").write_bytes(b"original")
            (path / "version.json").write_text('{}\n')
            subprocess.run([sys.executable, str(ROOT / "scripts/bfa_release.py"), "checksums", str(path)], check=True)
            entries = dict(line.split("  ")[::-1] for line in (path / "SHA256SUMS").read_text().splitlines())
            self.assertEqual(set(entries), {"package.zip", "version.json"})
            self.assertEqual(entries["package.zip"], hashlib.sha256(b"original").hexdigest())
            (path / "package.zip").write_bytes(b"tampered")
            self.assertNotEqual(entries["package.zip"], release.digest(path / "package.zip"))


if __name__ == "__main__":
    unittest.main()
