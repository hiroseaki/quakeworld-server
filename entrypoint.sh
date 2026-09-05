#!/bin/sh
set -eu

runtime=/nquake/ktx/runtime
cycle=${QW_MAPCYCLE_FILE:-/config/mapcycle.txt}
secret_file=${RCON_PASSWORD_FILE:-/run/secrets/rcon_password}

fail() {
  echo "quakeworld: $*" >&2
  exit 1
}

safe_text() {
  case "$2" in
    *'"'*|*'\\'*|*"
"*|*""*) fail "$1 contains an unsupported quote, backslash, or newline" ;;
  esac
}

uint() {
  case "$2" in ''|*[!0-9]*) fail "$1 must be a non-negative integer" ;; esac
}

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

[ -r /nquake/id1/pak0.pak ] || fail "missing /nquake/id1/pak0.pak; mount your legally obtained Quake data"
[ -r "$cycle" ] || fail "map cycle is not readable: $cycle"

hostname=${QW_HOSTNAME:-QuakeWorld FFA}
admin=${QW_ADMININFO:-}
country=${QW_COUNTRYCODE:-}
city=${QW_CITY:-}
coords=${QW_COORDS:-}
port=${QW_PORT:-27500}
maxclients=${QW_MAXCLIENTS:-16}
maxspectators=${QW_MAXSPECTATORS:-8}
timelimit=${QW_TIMELIMIT:-10}
fraglimit=${QW_FRAGLIMIT:-50}
memory=${QW_MEMORY_MB:-128}
masters=${QW_MASTER_SERVERS:-master.quakeservers.net:27000 qwmaster.ocrana.de:27000 master.quakeworld.nu:27000 qwmaster.fodquake.net:27000}

safe_text QW_HOSTNAME "$hostname"
safe_text QW_ADMININFO "$admin"
safe_text QW_COUNTRYCODE "$country"
safe_text QW_CITY "$city"
safe_text QW_COORDS "$coords"
uint QW_PORT "$port"
uint QW_MAXCLIENTS "$maxclients"
uint QW_MAXSPECTATORS "$maxspectators"
uint QW_TIMELIMIT "$timelimit"
uint QW_FRAGLIMIT "$fraglimit"
uint QW_MEMORY_MB "$memory"
[ "$port" -ge 1 ] && [ "$port" -le 65535 ] || fail "QW_PORT must be between 1 and 65535"
[ "$maxclients" -ge 1 ] && [ "$maxclients" -le 32 ] || fail "QW_MAXCLIENTS must be between 1 and 32"
[ "$maxspectators" -le 32 ] || fail "QW_MAXSPECTATORS must be no greater than 32"
for master in $masters; do
  case "$master" in *[!a-zA-Z0-9._:-]*) fail "QW_MASTER_SERVERS contains unsupported characters" ;; esac
done

if [ -r "$secret_file" ]; then
  rcon=$(tr -d '\r\n' < "$secret_file")
else
  rcon=${RCON_PASSWORD:-}
fi
[ -n "$rcon" ] || fail "provide an RCON password with a Docker secret or RCON_PASSWORD"
safe_text RCON_PASSWORD "$rcon"

maps=''
while IFS= read -r map || [ -n "$map" ]; do
  case "$map" in ''|'#'*) continue ;; esac
  case "$map" in *[!a-zA-Z0-9_+-]*) fail "invalid map name in map cycle: $map" ;; esac
  maps="$maps $map"
done < "$cycle"
set -- $maps
[ "$#" -ge 1 ] || fail "the map cycle must contain at least one map"

start_map=${QW_START_MAP:-}
if [ -n "$start_map" ]; then
  case "$start_map" in *[!a-zA-Z0-9_+-]*) fail "invalid QW_START_MAP: $start_map" ;; esac
else
  random=$(od -An -N4 -tu4 /dev/urandom | tr -d ' ')
  index=$((random % $# + 1))
  i=1
  for map in "$@"; do
    [ "$i" -ne "$index" ] || start_map=$map
    i=$((i + 1))
  done

  last_map=$(cat /nquake/logs/.last-start-map 2>/dev/null || true)
  if [ "$#" -gt 1 ] && [ "$start_map" = "$last_map" ]; then
    index=$((index % $# + 1))
    i=1
    for map in "$@"; do
      [ "$i" -ne "$index" ] || start_map=$map
      i=$((i + 1))
    done
  fi
fi

umask 077
mkdir -p "$runtime"
printf '%s\n' "$start_map" > /nquake/logs/.last-start-map

cat > "$runtime/server.cfg" <<EOF
hostname "$hostname"
sv_admininfo "$admin"
sv_serverip "0.0.0.0:$port"
maxclients $maxclients
maxspectators $maxspectators
timelimit $timelimit
fraglimit $fraglimit
set countrycode "$country"
set city "$city"
set coords "$coords"
setmaster $masters
EOF

cat > "$runtime/passwords.cfg" <<EOF
rcon_password "$rcon"
qtv_password ""
EOF

{
  echo 'set k_random_maplist 1'
  i=0
  for map in "$@"; do
    printf 'set k_ml_%d "%s"\n' "$i" "$map"
    i=$((i + 1))
  done
} > "$runtime/mapcycle.cfg"

echo "Starting $hostname on UDP $port (map: $start_map)"
exec /nquake/mvdsv -port "$port" -mem "$memory" -game ktx \
  +exec container-base.cfg +exec runtime/server.cfg +exec runtime/passwords.cfg \
  +exec runtime/mapcycle.cfg +map "$start_map"
