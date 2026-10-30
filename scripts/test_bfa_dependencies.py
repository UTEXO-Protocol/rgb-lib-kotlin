from pathlib import Path
import tempfile
import unittest

from verify_bfa_dependencies import verify_dependencies


PATCH = '''[patch.crates-io]
rgb-ops = { git = "ssh://git@github.com/rgb-tools-devs/rgb-ops.git", rev = "abcdef01" }
'''
SOURCE = 'git+ssh://git@github.com/rgb-tools-devs/rgb-ops.git?rev=abcdef01#' + 'abcdef01' + 'a' * 32
LOCK = '''version = 4
[[package]]
name = "rgb-ops"
version = "0.11.2-rc.1"
source = "SOURCE"
'''.replace('SOURCE', SOURCE)


class BfaDependencyTests(unittest.TestCase):
    def fixture(self, root, manifest=PATCH, lock=LOCK):
        uniffi = root / 'bindings/uniffi'
        uniffi.mkdir(parents=True)
        (root / 'Cargo.toml').write_text(PATCH)
        (root / 'Cargo.lock').write_text(LOCK)
        (uniffi / 'Cargo.toml').write_text('[workspace]\n' + manifest)
        (uniffi / 'Cargo.lock').write_text(lock)

    def test_consistent_pins_pass_without_changing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            before = {p: p.read_bytes() for p in root.rglob('Cargo.*')}
            verify_dependencies(root)
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_missing_patch_like_bfa4_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, manifest='', lock=LOCK.replace(SOURCE, 'registry+https://github.com/rust-lang/crates.io-index'))
            with self.assertRaisesRegex(ValueError, 'must match the root'):
                verify_dependencies(root)

    def test_older_source_without_root_overrides_remains_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / 'Cargo.toml').write_text('[workspace]\n')
            verify_dependencies(root)

    def test_patch_added_without_updating_lock_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, lock=LOCK.replace(SOURCE, 'registry+https://github.com/rust-lang/crates.io-index'))
            with self.assertRaisesRegex(ValueError, 'lockfile must pin'):
                verify_dependencies(root)

    def test_different_manifest_revision_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, manifest=PATCH.replace('abcdef01', '12345678'))
            with self.assertRaisesRegex(ValueError, 'must match the root'):
                verify_dependencies(root)

    def test_different_resolved_commit_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, lock=LOCK.replace('a' * 32, 'b' * 32))
            with self.assertRaisesRegex(ValueError, 'same Git commit'):
                verify_dependencies(root)

    def test_wrong_git_repository_or_revision_fails(self):
        for replacement in (SOURCE.replace('rgb-ops.git', 'different.git'),
                            SOURCE.replace('?rev=abcdef01', '?rev=12345678')):
            with self.subTest(source=replacement), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, lock=LOCK.replace(SOURCE, replacement))
                with self.assertRaisesRegex(ValueError, 'lockfile must pin'):
                    verify_dependencies(root)


if __name__ == '__main__':
    unittest.main()
