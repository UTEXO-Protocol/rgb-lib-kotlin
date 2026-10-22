#!/usr/bin/env python3
"""Reject incomplete Android packages before publishing them."""
import json
import os
from pathlib import Path
import shutil
import zipfile

version = os.environ["RELEASE_VERSION"]
source_sha = os.environ["SOURCE_SHA"]
aar = Path("android/build/outputs/aar/android-release.aar")
with zipfile.ZipFile(aar) as archive:
    for abi in ("arm64-v8a", "x86_64"):
        for library in ("librgblibuniffi.so", "libc++_shared.so"):
            assert archive.getinfo(f"jni/{abi}/{library}").file_size > 0
    assert archive.getinfo("classes.jar").file_size > 0
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
