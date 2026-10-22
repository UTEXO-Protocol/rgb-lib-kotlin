import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).with_name('package_bfa.py')
VERSION = '0.3.0-beta.7-bfa'
SHA = 'a' * 40


class AndroidPackageTests(unittest.TestCase):
    def package(self, root, missing=None, corrupt_staged=False):
        metadata = json.dumps({'source_commit': SHA, 'version': VERSION}).encode()
        aar = root / 'android/build/outputs/aar/android-release.aar'
        aar.parent.mkdir(parents=True)
        with zipfile.ZipFile(aar, 'w') as archive:
            for abi in ('arm64-v8a', 'x86_64'):
                for lib in ('librgblibuniffi.so', 'libc++_shared.so'):
                    name = f'jni/{abi}/{lib}'
                    if name != missing:
                        archive.writestr(name, b'binary')
            archive.writestr('classes.jar', b'classes')
            archive.writestr('assets/rgb-lib-bfa-version.json', metadata)
        meta = root / 'android/src/main/assets/rgb-lib-bfa-version.json'
        meta.parent.mkdir(parents=True)
        meta.write_bytes(metadata)
        staged = root / f'android/build/staging-deploy/com/utexo/rgb-lib-bfa-android/{VERSION}/rgb-lib-bfa-android-{VERSION}.aar'
        staged.parent.mkdir(parents=True)
        staged.write_bytes(b'wrong package' if corrupt_staged else aar.read_bytes())
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=root,
                              env={**os.environ, 'RELEASE_VERSION': VERSION, 'SOURCE_SHA': SHA},
                              capture_output=True, text=True)

    def test_complete_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.package(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((root / 'release-assets/version.json').read_text())['source_commit'], SHA)
            self.assertTrue((root / f'release-assets/rgb-lib-bfa-android-{VERSION}.aar').exists())

    def test_missing_emulator_library_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.package(Path(directory), missing='jni/x86_64/librgblibuniffi.so')
            self.assertNotEqual(result.returncode, 0)

    def test_maven_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.package(Path(directory), corrupt_staged=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Maven and release AAR differ', result.stderr)


if __name__ == '__main__':
    unittest.main()
