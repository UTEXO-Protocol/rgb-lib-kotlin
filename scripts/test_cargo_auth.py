import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
# Synthetic test credential; no account access or network requests are involved.
TEST_TOKEN = 'synthetic-test-token'


class CargoAuthTests(unittest.TestCase):
    def run_wrapped(self, command, data='', token=TEST_TOKEN):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, 'BFA_SOURCE_READ_TOKEN': token,
                   'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_SYSTEM': os.devnull,
                   'GIT_ASKPASS': '/usr/bin/false', 'SSH_ASKPASS': '/usr/bin/false'}
            return subprocess.run(
                ['bash', str(SCRIPTS / 'with_cargo_auth.sh'), *command],
                cwd=directory, input=data, text=True, capture_output=True, env=env,
            )

    def test_git_authenticates_each_private_dependency(self):
        for repo in ('rgb-consensus-s-bfa', 'rgb-ops-s-bfa', 'rgb-api-s-bfa', 'rgb-schemas-s-bfa'):
            for suffix in ('', '.git'):
                with self.subTest(repo=repo, suffix=suffix):
                    result = self.run_wrapped(
                        ['git', 'credential', 'fill'],
                        f'url=https://github.com/UTEXO-Protocol/{repo}{suffix}\n\n',
                    )
                    self.assertEqual(result.returncode, 0)
                    self.assertIn('username=x-access-token\n', result.stdout)
                    self.assertIn(f'password={TEST_TOKEN}\n', result.stdout)

    def test_upstream_ssh_urls_resolve_to_utexo_mirrors_without_network(self):
        for repo in ('rgb-consensus', 'rgb-ops', 'rgb-api', 'rgb-schemas'):
            with self.subTest(repo=repo):
                result = self.run_wrapped([
                    'git', 'ls-remote', '--get-url',
                    f'ssh://git@github.com/rgb-tools-devs/{repo}.git',
                ])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), f'https://github.com/UTEXO-Protocol/{repo}-s-bfa.git')
                self.assertNotIn(TEST_TOKEN, result.stdout + result.stderr)

    def test_unrelated_upstream_is_not_rewritten(self):
        url = 'ssh://git@github.com/rgb-tools-devs/unrelated.git'
        result = self.run_wrapped(['git', 'ls-remote', '--get-url', url])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), url)

    def test_git_config_does_not_contain_token(self):
        result = self.run_wrapped(['git', 'config', '--list'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(TEST_TOKEN, result.stdout + result.stderr)

    def test_unrelated_urls_do_not_receive_token(self):
        for url in (
            'https://github.com/another-org/rgb-consensus-s-bfa',
            'https://github.com/UTEXO-Protocol/unrelated',
            'https://github.com/UTEXO-Protocol/rgb-consensus-s-bfa-other',
            'https://github.com.evil.example/UTEXO-Protocol/rgb-consensus-s-bfa',
            'http://github.com/UTEXO-Protocol/rgb-consensus-s-bfa',
        ):
            with self.subTest(url=url):
                result = self.run_wrapped(['git', 'credential', 'fill'], f'url={url}\n\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(TEST_TOKEN, result.stdout + result.stderr)

    def test_missing_secret_fails_before_build(self):
        result = self.run_wrapped(['printf', 'build-started'], token='')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('build-started', result.stdout)
        self.assertIn('BFA_SOURCE_READ_TOKEN', result.stderr)

    def test_cargo_uses_git_cli_and_build_exit_status_is_preserved(self):
        result = self.run_wrapped(['bash', '-c', 'printf "%s" "$CARGO_NET_GIT_FETCH_WITH_CLI"; exit 23'])
        self.assertEqual(result.stdout, 'true')
        self.assertEqual(result.returncode, 23)

    def test_helper_does_not_store_credentials(self):
        result = self.run_wrapped(
            ['bash', str(SCRIPTS / 'cargo_git_credential.sh'), 'store'],
            f'protocol=https\nhost=github.com\npath=UTEXO-Protocol/rgb-consensus-s-bfa\npassword={TEST_TOKEN}\n\n',
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
