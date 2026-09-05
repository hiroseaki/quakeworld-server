#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

sh -n "$root/entrypoint.sh"
sh -n "$root/scripts/smoke-test.sh"
cc -Wall -Wextra -Werror -fsyntax-only "$root/src/qw-healthcheck.c"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker compose -f "$root/compose.yaml" config --quiet
fi

echo "Static checks passed"
