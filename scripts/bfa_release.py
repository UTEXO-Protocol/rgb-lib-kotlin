#!/usr/bin/env python3
"""Validate the BFA release contract and record artifact provenance (stdlib only)."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib


def git_sha(directory):
    return subprocess.check_output(
        ["git", "-C", str(directory), "rev-parse", "HEAD"], text=True
    ).strip()


def validate(version, source_sha):
    version = version.removeprefix("v")
    # A separate prerelease namespace prevents collisions with ordinary rgb-lib.
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?-bfa", version):
        raise ValueError("Expected a BFA version such as 0.3.0-beta.7-bfa")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("source_sha must be a full lowercase 40-character commit SHA")
    return version, source_sha


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    command = sys.argv[1]
    if command == "validate":
        version, sha = validate(os.environ["VERSION_INPUT"], os.environ["SOURCE_SHA_INPUT"])
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"version={version}\nsource_sha={sha}\n")
    elif command == "metadata":
        platform, output_path = sys.argv[2:]
        version, sha = validate(os.environ["RELEASE_VERSION"], os.environ["SOURCE_SHA"])
        source = Path("rgb-lib")
        if git_sha(source) != sha:
            raise ValueError("Checked-out source differs from requested source_sha")
        metadata = {
            "schema_version": 1,
            "version": version,
            "source_repository": "UTEXO-Protocol/rgb-lib-bfa",
            "source_commit": sha,
            "source_version": tomllib.loads((source / "Cargo.toml").read_text())["package"]["version"],
            "source_lock_sha256": digest(source / "bindings/uniffi/Cargo.lock"),
            "bindings_repository": os.environ["GITHUB_REPOSITORY"],
            "bindings_commit": git_sha(Path(".")),
            "build_profile": "release",
            "rust_version": subprocess.check_output(["rustc", "--version"], text=True).strip(),
            "platform": platform,
            "targets": {
                "android": ["aarch64-linux-android", "x86_64-linux-android"],
                "apple": ["aarch64-apple-ios", "aarch64-apple-ios-sim", "x86_64-apple-ios", "aarch64-apple-darwin", "x86_64-apple-darwin"],
            }[platform],
            "workflow_run": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        }
        if platform == "android":
            metadata.update(min_android_api=21, android_ndk=os.environ["NDK_VERSION"], maven_artifact="com.utexo:rgb-lib-bfa-android")
        else:
            metadata.update(min_ios_version="16.0", min_macos_version="12.0", xcode=subprocess.check_output(["xcodebuild", "-version"], text=True).strip())
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metadata, indent=2) + "\n")
    elif command == "checksums":
        directory = Path(sys.argv[2])
        files = sorted(p for p in directory.iterdir() if p.is_file() and p.name != "SHA256SUMS")
        if not files:
            raise ValueError("No release assets found")
        (directory / "SHA256SUMS").write_text("".join(f"{digest(p)}  {p.name}\n" for p in files))
    else:
        raise ValueError(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
