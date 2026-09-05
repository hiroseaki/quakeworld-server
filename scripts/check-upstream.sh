#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
current_mvdsv=$(sed -n 's/^ARG MVDSV_VERSION=//p' "$root/Dockerfile")
current_ktx=$(sed -n 's/^ARG KTX_VERSION=//p' "$root/Dockerfile")

latest_release() {
  curl -fsSL -H 'Accept: application/vnd.github+json' \
    "https://api.github.com/repos/QW-Group/$1/releases/latest" \
    | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | head -1
}

latest_mvdsv=$(latest_release mvdsv)
latest_ktx=$(latest_release ktx)

printf 'MVDSV: pinned %s, latest %s\n' "$current_mvdsv" "$latest_mvdsv"
printf 'KTX:   pinned %s, latest %s\n' "$current_ktx" "$latest_ktx"

[ "$current_mvdsv" = "$latest_mvdsv" ] && [ "$current_ktx" = "$latest_ktx" ]
