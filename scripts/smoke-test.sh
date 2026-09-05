#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
image=${QW_TEST_IMAGE:-quakeworld-server:test}
pak0=${QUAKE_PAK0:-$root/data/id1/pak0.pak}

command -v docker >/dev/null 2>&1 || { echo "Docker is required" >&2; exit 1; }
[ -r "$pak0" ] || {
  echo "Set QUAKE_PAK0 to a legally obtained pak0.pak to run the integration test." >&2
  exit 2
}

work=$(mktemp -d)
container=quakeworld-smoke-$$
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  rm -rf "$work"
}
trap cleanup EXIT INT TERM

mkdir -p "$work/id1" "$work/logs" "$work/demos"
cp "$pak0" "$work/id1/pak0.pak"
printf 'dm1\n' > "$work/mapcycle.txt"
printf 'smoke-test-password\n' > "$work/rcon_password"
chmod 600 "$work/rcon_password"

docker build -t "$image" "$root"
docker run -d --name "$container" \
  --init \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 128 \
  --tmpfs /nquake/ktx/runtime:uid=10001,gid=10001,mode=0700 \
  --tmpfs /tmp:uid=10001,gid=10001,mode=0700 \
  -e QW_HOSTNAME="Container smoke test" \
  -v "$work/id1:/nquake/id1:ro" \
  -v "$work/logs:/nquake/logs" \
  -v "$work/demos:/nquake/ktx/demos" \
  -v "$work/mapcycle.txt:/config/mapcycle.txt:ro" \
  -v "$work/rcon_password:/run/secrets/rcon_password:ro" \
  "$image" >/dev/null

i=0
while [ "$i" -lt 30 ]; do
  status=$(docker inspect --format '{{.State.Health.Status}}' "$container")
  [ "$status" != healthy ] || { echo "Integration test passed"; exit 0; }
  [ "$status" != unhealthy ] || break
  i=$((i + 1))
  sleep 1
done

docker logs "$container" >&2
exit 1
