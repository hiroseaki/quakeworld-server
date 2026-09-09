#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
for script in "$root/entrypoint.sh" "$root"/scripts/*.sh; do sh -n "$script"; done
python3 -m unittest discover -s "$root/tests" -p 'test_*.py'
if command -v docker >/dev/null 2>&1; then
  docker compose -f "$root/compose.yaml" --profile '*' config --quiet
  QW_IMAGE=example/quakeworld:test docker compose -f "$root/examples/compose.registry.yaml" --profile '*' config --quiet
fi
echo 'Static and configuration checks passed'
