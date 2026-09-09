#!/bin/sh
set -eu
exec python3 /usr/local/lib/quakeworld/entrypoint.py "$@"
