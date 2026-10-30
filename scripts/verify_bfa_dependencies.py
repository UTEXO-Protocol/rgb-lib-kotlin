#!/usr/bin/env python3
"""Reject source revisions whose standalone UniFFI workspace lost RGB patches."""
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import parse_qs, urlsplit


def read_toml(path):
    return tomllib.loads(path.read_text())


def locked_source(lock, name, patch):
    matches = []
    for package in lock['package']:
        if package['name'] != name:
            continue
        source = package.get('source', '')
        url, _, query = source.partition('?')
        parsed = urlsplit(source)
        if (url == 'git+' + patch['git']
                and parse_qs(query.partition('#')[0]).get('rev') == [patch['rev']]
                and re.fullmatch(r'[0-9a-f]{40}', parsed.fragment)):
            matches.append((package['version'], source))
    if len(matches) != 1:
        raise ValueError(f'{name}: lockfile must pin the patched Git revision {patch["rev"]}')
    return matches[0]


def verify_dependencies(root):
    uniffi = root / 'bindings/uniffi'
    patches = read_toml(root / 'Cargo.toml').get('patch', {}).get('crates-io', {})
    overrides = read_toml(uniffi / 'Cargo.toml').get('patch', {}).get('crates-io', {})
    root_lock = read_toml(root / 'Cargo.lock')
    uniffi_lock = read_toml(uniffi / 'Cargo.lock')
    # Older BFA releases declare Git dependencies directly and need no overrides.
    for name, patch in patches.items():
        if overrides.get(name) != patch:
            raise ValueError(f'{name}: bindings/uniffi/Cargo.toml must match the root [patch.crates-io]')
        if 'git' not in patch or 'rev' not in patch:
            raise ValueError(f'{name}: BFA releases require a pinned Git rev')
        package = patch.get('package', name)
        if locked_source(root_lock, package, patch) != locked_source(uniffi_lock, package, patch):
            raise ValueError(f'{name}: root and UniFFI lockfiles must pin the same Git commit and version')


if __name__ == '__main__':
    try:
        verify_dependencies(Path(sys.argv[1] if len(sys.argv) > 1 else 'rgb-lib'))
    except (ValueError, KeyError, OSError) as error:
        sys.exit(f'BFA dependency preflight failed: {error}. '
                 'Use a source revision with committed UniFFI patches and lockfile '
                 '(bfa.4 is incompatible); do not remove --locked to bypass this check.')
    print('BFA dependency preflight passed.')
