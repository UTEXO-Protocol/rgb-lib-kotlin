#!/usr/bin/env bash
# Git credential helper: never store credentials or serve unrelated repositories.
set -euo pipefail
[[ "${1:-}" == get ]] || exit 0

protocol='' host='' path=''
while IFS='=' read -r key value; do
  [[ -n "$key" ]] || break
  case "$key" in
    protocol) protocol="$value" ;;
    host) host="$value" ;;
    path) path="$value" ;;
  esac
done

[[ "$protocol" == https && "$host" == github.com ]] || exit 0
case "${path%.git}" in
  UTEXO-Protocol/rgb-consensus-s-bfa|UTEXO-Protocol/rgb-ops-s-bfa|UTEXO-Protocol/rgb-api-s-bfa|UTEXO-Protocol/rgb-schemas-s-bfa)
    [[ -n "${BFA_SOURCE_READ_TOKEN:-}" ]] || exit 1
    printf 'username=x-access-token\npassword=%s\n' "$BFA_SOURCE_READ_TOKEN"
    ;;
esac
