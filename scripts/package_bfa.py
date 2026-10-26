#!/usr/bin/env python3
"""Reject incomplete Android packages before publishing them."""
import io
import json
import os
from pathlib import Path
import shutil
import zipfile

from verify_bfa_bindings import verify_bindings

version = os.environ["RELEASE_VERSION"]
source_sha = os.environ["SOURCE_SHA"]
aar = Path("android/build/outputs/aar/android-release.aar")
verify_bindings(Path("android/src/main/kotlin"))
with zipfile.ZipFile(aar) as archive:
    for abi in ("arm64-v8a", "x86_64"):
        assert archive.getinfo(f"jni/{abi}/librgblibuniffi.so").file_size > 0
    assert not any(name.endswith("/libc++_shared.so") for name in archive.namelist()), \
        "AAR must not bundle libc++_shared.so: it conflicts with React Native"
    with zipfile.ZipFile(io.BytesIO(archive.read("classes.jar"))) as classes:
        assert classes.getinfo("com/utexo/Rgb_libKt.class").file_size > 0
        assert not any(name.startswith("uniffi/rgb_lib/") for name in classes.namelist()), \
            "AAR contains stale uniffi.rgb_lib classes; clean and rebuild"
    metadata = json.loads(archive.read("assets/rgb-lib-bfa-version.json"))
    assert metadata["source_commit"] == source_sha
    assert metadata["version"] == version
output = Path("release-assets")
output.mkdir(exist_ok=True)
shutil.copyfile(aar, output / f"rgb-lib-bfa-android-{version}.aar")
shutil.copyfile("android/src/main/assets/rgb-lib-bfa-version.json", output / "version.json")
# The release download is exactly the AAR staged for Maven Central.
staged = Path(f"android/build/staging-deploy/com/utexo/rgb-lib-bfa-android/{version}/rgb-lib-bfa-android-{version}.aar")
assert staged.read_bytes() == aar.read_bytes(), "Maven and release AAR differ"
