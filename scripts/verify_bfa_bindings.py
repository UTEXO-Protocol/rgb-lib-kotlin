"""Check generated Kotlin, rather than trusting a config bindgen may ignore."""
from pathlib import Path
import re


def verify_bindings(root: Path) -> None:
    expected = root / "com/utexo/rgb_lib.kt"
    generated = sorted(root.rglob("rgb_lib.kt"))
    if generated != [expected]:
        raise ValueError(f"Expected only {expected}; found {generated}. Clean and regenerate bindings.")
    source = expected.read_text()
    if not re.search(r"^package com\.utexo\s*;?\s*$", source, re.MULTILINE):
        raise ValueError("Generated rgb_lib.kt must use package com.utexo")
    loader = re.search(
        r"^private fun findLibraryName\([^\n]*\)\s*:\s*String\s*\{(.*?)^\}",
        source, re.MULTILINE | re.DOTALL,
    )
    if not loader or not re.search(r'^\s*return "rgblibuniffi"\s*$', loader[1], re.MULTILINE):
        raise ValueError("Generated rgb_lib.kt must load rgblibuniffi by default; check bfa-uniffi.toml")
