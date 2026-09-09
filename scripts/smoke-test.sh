#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
image=${QW_TEST_IMAGE:-quakeworld-server:test}
if [ "${QW_SKIP_BUILD:-0}" != 1 ]; then docker build -t "$image" "$root"; fi
exec python3 "$root/tests/integration.py" "$image"
