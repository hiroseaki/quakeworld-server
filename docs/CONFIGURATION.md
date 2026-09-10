# Configuration

Variables below are the **image's** interface. Compose passes `.env` to each
container, then applies service-specific settings. In Compose, `QW_SERVICE`,
`QW_MODE`, and internal `QW_PORT=27500` are fixed per service. Use `FFA_PORT`,
`KTX1_PORT` … `KTX4_PORT` to change published host ports. `FFA_HOSTNAME`,
`KTX1_HOSTNAME` … `KTX4_HOSTNAME` override names; `KTX1_MODE` … `KTX4_MODE`
choose each match server's default mode.

## Role and game settings

| Variable | Image default | Purpose |
| --- | --- | --- |
| `QW_SERVICE` | `server` | `server`, `qtv`, or `qwfwd` |
| `QW_MODE` | `ffa` | `ffa`, `ktx`, `ctf` or `ra`; game role only |
| `QW_HOSTNAME` | derived from mode | Server browser name |
| `QW_PORT` | `27500` | Internal UDP port; also QTV TCP port when enabled |
| `QW_DEFAULT_MODE` | `1on1` | KTX: `1on1`, `2on2`, `3on3`, `4on4`, `10on10`, `ffa` |
| `QW_MAXCLIENTS` | `16` | Player limit, 1–32 |
| `QW_MAXSPECTATORS` | `8` | Spectator limit, 0–32 |
| `QW_START_MAP` | random FFA; `dm3` for KTX | Must exist in mounted game data |
| `QW_MAPCYCLE_FILE` | Mode-specific file under `/etc/quakeworld/` | FFA/CTF/RA map list; Compose uses `config/mapcycle.txt`, `config/ctf-mapcycle.txt`, `config/ra-mapcycle.txt` |
| `QW_MAPCYCLE_RANDOM` | `1` for FFA; `0` otherwise | Random (1) or sequential (0) rotation |
| `QW_CTF_HOOK` | `1` | CTF grappling hook, 0 or 1 |
| `QW_CTF_RUNES` | `1` | CTF runes, 0 or 1 |
| `QW_TIMELIMIT` | `10` | FFA/CTF/RA minutes, 0–1440 |
| `QW_FRAGLIMIT` | `50` | FFA frag limit; CTF defaults to 0, RA to 10; 0 disables |
| `QW_MEMORY_MB` | `128` | MVDSV memory allocation, 32–4096 MB; raise container memory limit too if needed |
| `QW_ADMININFO` | empty | Public contact information |
| `QW_COUNTRYCODE`, `QW_CITY`, `QW_COORDS` | empty | Public location metadata |
| `QW_MASTER_SERVERS` | QW masters | Space-separated addresses; empty disables registration |
| `QW_QTV_ENABLED` | `0` | 1 enables TCP stream listener; Compose defaults to 1 |
| `QW_DEMO_MAX_MB` | `1024` | MVDSV demo directory limit |
| `QW_DEMO_FILE_MAX_MB` | `64` | MVDSV individual demo limit |
| `QW_CONFIG_FILE` | `/config/local-<service>.cfg` | Optional trusted custom configuration |

FFA does not repeat its last startup map when alternatives exist. Match servers
use their selected mode's rules; FFA time/frag limits are not imposed on them.
Allowed match modes exclude CTF because no CTF asset pack is bundled.

Text and password values reject control characters, quotes, backslashes, semicolons
and dollar signs instead of interpolating them into console commands. Use a long
random password without those characters. Map names and numeric settings are validated.

## Passwords

| Variable | Underlying setting | Empty value |
| --- | --- | --- |
| `QW_RCON_PASSWORD` | MVDSV `rcon_password` | RCON disabled |
| `QW_ADMIN_PASSWORD` | KTX `k_admincode` | KTX admins disabled (`k_admins 0`) |
| `QW_PASSWORD` | MVDSV `password` | Public player access |
| `QW_SPECTATOR_PASSWORD` | MVDSV `spectator_password` | Public spectator access |
| `QW_QTV_PASSWORD` | MVDSV upstream `qtv_password` | No stream password |
| `QTV_PASSWORD` | QTV downstream `qtv_password` | Public QTV viewing |

KTX login is `admin <password>` from the client console. Do not use the reserved
KTX value `none` as an admin password. RCON retains MVDSV's default authenticated
SHA1/timestamp mode (`sv_crypt_rcon 1`); configure a compatible client such as ezQuake
with `cl_crypt_rcon 1`. These are separate administration mechanisms.

Each password supports a corresponding `_FILE` variable, e.g.
`QW_RCON_PASSWORD_FILE=/run/secrets/ffa-rcon`. The file takes precedence over the
environment value; an explicitly configured missing/unreadable file is an error.
`RCON_PASSWORD` and `RCON_PASSWORD_FILE` remain compatibility aliases. New names
win over the corresponding aliases. No password is required to start a public server.

`.env` is ignored by Git and Docker. Environment secrets are visible to users
with Docker inspection privileges. For file secrets, Compose mounts `.secrets`
read-only. On Linux prepare the directory as root-owned `0711` and the individual
files as `10001:10001`, mode `0400`, so the non-root process can traverse and read
them without granting other host users access. Docker Compose file-backed secrets
do not remap file ownership for you.

Shared `.env` passwords apply to all game containers. Override a service in Compose
for different credentials, for example:

```yaml
services:
  ktx-1:
    environment:
      QW_RCON_PASSWORD: ${KTX1_RCON_PASSWORD:-}
      QW_ADMIN_PASSWORD: ${KTX1_ADMIN_PASSWORD:-}
```

Do not set a shared `_FILE` if you intend a per-service environment value to win.
Restart/recreate containers after changing environment settings.

## QTV and qwfwd

| Variable | Default | Purpose |
| --- | --- | --- |
| `QTV_PORT` | `28000` | QTV/HTTP TCP listener |
| `QTV_HOSTNAME` | `QuakeWorld TV` | Browser name |
| `QTV_PUBLIC_ADDRESS` | empty | Public host:port advertised to clients |
| `QTV_MAXCLIENTS` | `100` | Downstream viewer limit |
| `QTV_DELAY` | `10` | Stream delay in seconds |
| `QTV_SOURCES` | empty | Space-separated game host:port addresses |
| `QTV_SOURCES_FILE` | unset | JSON source list; overrides `QTV_SOURCES` |
| `QWFWD_PORT` | `30000` | UDP listener |
| `QWFWD_HOSTNAME` | `QuakeWorld proxy` | Browser name |
| `QWFWD_PUBLIC_ADDRESS` | empty | Public host:port |

`QW_MASTER_SERVERS` applies to all roles. QTV sources use the shared
`QW_QTV_PASSWORD` unless overridden in their JSON entry. For different passwords:

```json
[
  {"address": "ffa:27500", "password_file": "/run/secrets/ffa-stream"},
  {"address": "ktx-1:27500", "password_file": "/run/secrets/ktx1-stream"}
]
```

An entry can also contain `password`; treat such a JSON file as a secret and keep
it in `.secrets`, never under tracked `config`. The paths refer to the QTV container.
When QTV runs remotely, publish the game servers' TCP ports and use reachable
public addresses instead of Compose DNS names. The stream password is independent
of RCON/admin and of the QTV viewer password.

QTV HTTP demo uploads and asset downloads are disabled in the supplied configuration.
qwfwd's usefulness depends on its network location; running it beside the game
server does not automatically improve latency.

## Custom configuration and storage

Create `config/local-server.cfg`, `config/local-qtv.cfg`, or `config/local-qwfwd.cfg`
for trusted console commands. An explicit `QW_CONFIG_FILE` must be readable.
Game startup and last-player reset run the project's `server.cfg`, never upstream's
password examples. Custom game commands run before generated passwords; passwords
therefore remain environment/file-controlled. FFA also reapplies its configuration
on mode/map initialization. KTX usermode rules may override custom gameplay cvars;
mount the relevant `configs/usermodes/<mode>/*.cfg` for detailed mode customization.
Do not overwrite the whole `/nquake/ktx` directory, which contains the game module.

Docker's `local` logging driver rotates console logs (3 × 10 MB per container).
Native unbounded player/RCON log files are not enabled by default. Named `*-logs`
volumes retain startup state; `*-demos` volumes retain recordings. MVDSV enforces
its demo limits during recording/cleanup, not as a hard filesystem quota; a write
can briefly exceed a threshold. Back up important demos before automatic cleanup.

If you replace named volumes with bind mounts, prepare writable directories for
UID/GID 10001. PAK/maps/locs mounts only need read/traverse permissions. No runtime
root user or automatic host ownership changes are used.

## CTF and Rocket Arena

Use the `ctf` and `ra` Compose profiles, independently or alongside existing
services. Default host ports are UDP 27505 and 27506. Each has separate persistent
logs/demos and reads the same game data. Add `ctf:27500` and `ra:27500` to
`QTV_SOURCES` if you want their streams.

CTF is public matchless play with red/blue teams, hook and runes enabled. It uses
KTX's built-in fallback visuals (`k_ctf_custom_models 0`), so no CTF model pack
is needed. KTX's original-map entity definitions are bundled under
`/nquake/ktx/maps/ctf`. Startup checks require both flag entities for every map in
the rotation and the selected start map. Custom Quake BSP maps may contain their
own flags; otherwise supply `data/maps/ctf/<map>.ent`. Bundled definitions take
precedence for their original map names; use distinct names for modified maps.

Rocket Arena is KTX's duel-based Rocket Arena, including its challenger queue.
Players ready up to start the match. It is not Clan Arena or a packaged original
Rocket Arena distribution. Matchless mode is deliberately disabled because KTX
forces matchless non-CTF games back to FFA. On match end, the rotation advances
when a client leaves the scoreboard with attack/jump, as in normal QuakeWorld.
CTF uses the same scoreboard transition; `next_map` votes end its current game.

Both default rotations contain `e1m2`, `e1m3`, `e1m5`, available in shareware.
Edit `config/ctf-mapcycle.txt` and `config/ra-mapcycle.txt` (one map per line,
`#` comments). Rotation is sequential by default; start selection is random
unless `CTF_START_MAP`/`RA_START_MAP` is set. Missing BSPs or CTF flags fail startup.
Use `CTF_MAPCYCLE_RANDOM=1` or `RA_MAPCYCLE_RANDOM=1` for random rotation.

Compose isolates the new limits from FFA's shared variables: use
`CTF_TIMELIMIT`, `CTF_FRAGLIMIT`, `RA_TIMELIMIT`, `RA_FRAGLIMIT`. Direct `docker run`
uses `QW_TIMELIMIT` and `QW_FRAGLIMIT`. Set `QW_MODE=ctf` or `QW_MODE=ra`; no
`QW_DEFAULT_MODE` override is needed for these profiles.
