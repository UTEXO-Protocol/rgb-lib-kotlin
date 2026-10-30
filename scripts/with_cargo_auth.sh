#!/usr/bin/env bash
# Authenticate private Git dependencies only for the wrapped build process.
set -euo pipefail

if [[ -z "${BFA_SOURCE_READ_TOKEN:-}" ]]; then
  echo 'BFA_SOURCE_READ_TOKEN must have Contents read access to the private RGB dependency repositories.' >&2
  exit 1
fi
if [[ $# -eq 0 ]]; then
  echo 'Usage: bash scripts/with_cargo_auth.sh <build command> [arguments...]' >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CARGO_NET_GIT_FETCH_WITH_CLI=true
export GIT_TERMINAL_PROMPT=0
# Override inherited helpers without writing the token into Git config or URLs.
export GIT_CONFIG_COUNT=3
export GIT_CONFIG_KEY_0=credential.helper
export GIT_CONFIG_VALUE_0=''
export GIT_CONFIG_KEY_1=credential.https://github.com.helper
export GIT_CONFIG_VALUE_1="!bash \"$script_dir/cargo_git_credential.sh\""
export GIT_CONFIG_KEY_2=credential.https://github.com.useHttpPath
export GIT_CONFIG_VALUE_2=true

# Keep Cargo's pinned source identity; only change Git's transport to our mirrors.
# Credentials are supplied by the scoped helper, never embedded in these URLs.
for repo in rgb-consensus rgb-ops rgb-api rgb-schemas; do
  export "GIT_CONFIG_KEY_${GIT_CONFIG_COUNT}=url.https://github.com/UTEXO-Protocol/${repo}-s-bfa.git.insteadOf"
  export "GIT_CONFIG_VALUE_${GIT_CONFIG_COUNT}=ssh://git@github.com/rgb-tools-devs/${repo}.git"
  GIT_CONFIG_COUNT=$((GIT_CONFIG_COUNT + 1))
done

exec "$@"
