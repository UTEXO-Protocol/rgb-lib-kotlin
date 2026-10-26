import io
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
KOTLIN = '''package com.utexo
private fun findLibraryName(componentName: String): String {
    val libOverride = System.getProperty("uniffi.component.$componentName.libraryOverride")
    if (libOverride != null) {
        return libOverride
    }
    return "rgblibuniffi"
}
'''


class AndroidPackageTests(unittest.TestCase):
    def package(self, root, missing=None, corrupt_staged=False, bundled_cpp=None,
                kotlin=KOTLIN, package='com/utexo', stale_source=False,
                class_package='com/utexo', stale_classes=False):
        metadata = json.dumps({'source_commit': SHA, 'version': VERSION}).encode()
        aar = root / 'android/build/outputs/aar/android-release.aar'
        aar.parent.mkdir(parents=True)
        bindings = root / f'android/src/main/kotlin/{package}/rgb_lib.kt'
        bindings.parent.mkdir(parents=True)
        bindings.write_text(kotlin)
        if stale_source:
            stale = root / 'android/src/main/kotlin/uniffi/rgb_lib/rgb_lib.kt'
            stale.parent.mkdir(parents=True)
            stale.write_text(KOTLIN.replace('com.utexo', 'uniffi.rgb_lib'))
        jar = io.BytesIO()
        with zipfile.ZipFile(jar, 'w') as classes:
            classes.writestr(f'{class_package}/Rgb_libKt.class', b'class fixture')
            if stale_classes:
                classes.writestr('uniffi/rgb_lib/UniffiLib.class', b'stale class fixture')
        with zipfile.ZipFile(aar, 'w') as archive:
            for abi in ('arm64-v8a', 'x86_64'):
                name = f'jni/{abi}/librgblibuniffi.so'
                if name != missing:
                    archive.writestr(name, b'binary')
            if bundled_cpp:
                archive.writestr(f'jni/{bundled_cpp}/libc++_shared.so', b'binary')
            archive.writestr('classes.jar', jar.getvalue())
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

    def test_bundled_cpp_fails_for_each_abi(self):
        for abi in ('arm64-v8a', 'x86_64'):
            with self.subTest(abi=abi), tempfile.TemporaryDirectory() as directory:
                result = self.package(Path(directory), bundled_cpp=abi)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('must not bundle libc++_shared.so', result.stderr)

    def test_ignored_config_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.package(Path(directory), package='uniffi/rgb_lib',
                                  kotlin=KOTLIN.replace('com.utexo', 'uniffi.rgb_lib')
                                  .replace('rgblibuniffi', 'uniffi_rgb_lib'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Clean and regenerate bindings', result.stderr)

    def test_default_library_fails_even_with_correct_name_in_comment(self):
        with tempfile.TemporaryDirectory() as directory:
            kotlin = KOTLIN.replace('"rgblibuniffi"', '"uniffi_rgb_lib"') + '// rgblibuniffi\n'
            result = self.package(Path(directory), kotlin=kotlin)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('must load rgblibuniffi by default', result.stderr)

    def test_wrong_package_declaration_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.package(Path(directory), kotlin=KOTLIN.replace('com.utexo', 'uniffi.rgb_lib'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('must use package com.utexo', result.stderr)

    def test_stale_generated_source_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.package(Path(directory), stale_source=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Clean and regenerate bindings', result.stderr)

    def test_wrong_compiled_package_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.package(Path(directory), class_package='uniffi/rgb_lib')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('com/utexo/Rgb_libKt.class', result.stderr)

    def test_stale_compiled_package_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.package(Path(directory), stale_classes=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('stale uniffi.rgb_lib classes', result.stderr)


if __name__ == '__main__':
    unittest.main()
