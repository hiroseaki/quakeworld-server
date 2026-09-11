# QuakeWorld Server Docker

One image for MVDSV/KTX **FFA, CTF, Rocket Arena and match servers**, **QTV**, and **qwfwd**.
Run one process per container. The supplied Compose file can start one FFA,
four match servers, CTF, Rocket Arena, a shared QTV, and a proxy with a single command.

- MVDSV development builds; all upstream revisions pinned in Dockerfile
- Native amd64 and arm64 CI tests
- UID/GID 10001, read-only root filesystem, dropped capabilities
- Environment settings and optional password files
- Protocol health checks, bounded Docker console logs, demo size limits
- No Quake PAK files or third-party map packs in Git or the image
- Corresponding upstream source and licenses under `/usr/src/quakeworld`

## Quick start

Requires Docker Engine/Desktop and **Docker Compose 2.24+**, plus legally obtained
Quake data. GitHub and registry accounts are not needed for local use.

```sh
make setup
cp /path/to/pak0.pak pak_files/pak0.pak
cp /path/to/pak1.pak pak_files/pak1.pak
# Edit .env: choose profiles, server names and passwords.
make up
```

`make setup` preserves existing `.env` and game files. The default configuration
starts FFA on UDP 27500. Both PAKs are required for the default rotation; see
[game data](docs/GAME-DATA.md) for shareware-only operation.

Choose services with `COMPOSE_PROFILES` in `.env`, or override it per invocation:

```sh
COMPOSE_PROFILES=ffa docker compose up -d --build
COMPOSE_PROFILES=ktx docker compose up -d --build
COMPOSE_PROFILES=ffa,ktx,qtv,proxy docker compose up -d --build
```

Profiles select services to start; they do not stop services already running.
Use `docker compose stop ffa` to stop one service or `make down` to stop all.
Named volumes survive `make down`; `docker compose down -v` deletes them.
To run just one match service: `docker compose up -d --build ktx-1`.

| Service | Role | Published port | Default match mode |
| --- | --- | --- | --- |
| `ffa` | FFA | 27500/UDP | matchless FFA |
| `ktx-1` | Match server | 27501/UDP | 1on1 |
| `ktx-2` | Match server | 27502/UDP | 1on1 |
| `ktx-3` | Match server | 27503/UDP | 2on2 |
| `ktx-4` | Match server | 27504/UDP | 4on4 |
| `ctf` | Public CTF | 27505/UDP | matchless CTF |
| `ra` | Rocket Arena | 27506/UDP | duel with challenger queue |
| `qtv` | Shared match streams | 28000/TCP | — |
| `qwfwd` | Player proxy | 30000/UDP | — |

Local client: `connect 127.0.0.1:27500`. Open the chosen UDP ports in your host
firewall/router for public play. QTV's HTTP stream list is at
[localhost:28000](http://localhost:28000/).

## Configuration and persistence

[Configuration reference](docs/CONFIGURATION.md) covers every environment variable,
secret precedence, custom configs, public addresses, and separate per-server passwords.

All game containers read the same PAKs, maps and locs. Each has its own named
log/state and demo volumes. Docker initializes volume ownership from the image,
so standard installation does not need host `chown` or a root entrypoint.
Runtime configs and credentials live in private tmpfs and are regenerated on start.

Use `QTV_SOURCES` to list only the services you actually run. QTV retries sources
that are temporarily unavailable. It connects to game containers on TCP 27500
inside the Compose network; those ports are not published to the host. Configure
`QTV_PUBLIC_ADDRESS` and `QWFWD_PUBLIC_ADDRESS` with your public hostname and port.
QTV and qwfwd can also run independently on another host, without PAK files.

## Published images

See [publishing](docs/PUBLISHING.md) for GitHub/GHCR and optional Docker Hub setup.
Use the registry Compose file from the repository root:

```sh
export QW_IMAGE=ghcr.io/hiroseaki/quakeworld-server:0.2.0
COMPOSE_PROFILES=ffa,ktx,qtv,proxy docker compose \
  --project-directory . -f examples/compose.registry.yaml up -d
```

## Verification

```sh
make check
python3 scripts/fetch-ra-maps.py
make smoke
# Optional: test against locally downloaded original shareware instead.
./scripts/fetch-shareware.sh
QUAKE_PAK_DIR="$PWD/.cache/quake-shareware/id1" make smoke
```

Integration tests create an isolated internal Docker network with no published
ports, start all nine services, check modes/RCON across resets and map changes,
exercise a client lifecycle, verify QTV streams and forward a connection through
qwfwd. Test containers are removed afterwards. This is protocol-level verification;
a full played match with a graphical client remains a release acceptance check.

Upstream monitoring opens a draft PR with changed pins; publishing requires a
version tag and successful tests. Source commits are pinned, but base image tags
and Debian packages can change, so builds are not claimed to be bit-for-bit identical.

## Licenses

Container glue is MIT; upstream licenses accompany source in the image. Game data
retains its original license and is supplied separately. See
[third-party notices](THIRD_PARTY_NOTICES.md) and [security](SECURITY.md).

## CTF and Rocket Arena

Available from **v0.2.0**. Clone this repository, run `make setup`, provide
`pak_files/pak0.pak` and `pak_files/pak1.pak`, and set your passwords in `.env`.
For the corrected Rocket Arena rotation, install the two separate arena maps:

```sh
python3 scripts/fetch-ra-maps.py
```

This downloads checksum-pinned `arena3.bsp` and `arena5.bsp` into `data/maps`.
These community maps are not part of `pak1.pak`. KTX entity definitions for both
arenas are bundled in the new image. This rotation correction requires a local
build until a release newer than `0.2.0` is published; use the build command below.

Start both using the published image (run from the repository root):

```sh
export QW_IMAGE=ghcr.io/hiroseaki/quakeworld-server:0.2.0
COMPOSE_PROFILES=ctf,ra docker compose \
  --project-directory . -f examples/compose.registry.yaml up -d
```

Use `COMPOSE_PROFILES=ctf` or `COMPOSE_PROFILES=ra` for just one. To build locally:

```sh
COMPOSE_PROFILES=ctf,ra docker compose up -d --build
```

Connect from your QuakeWorld client (replace localhost with your server address):

```text
connect 127.0.0.1:27505  // CTF
connect 127.0.0.1:27506  // Rocket Arena
```

CTF is public matchless play with red/blue teams, grappling hook and runes.
Rocket Arena uses KTX's duel mode with a winner/challenger queue; players use
`ready` to begin. At the scoreboard, attack/jump advances to the next map.
Open UDP 27505 and/or 27506 in your firewall/router for public access.

Edit the separate rotation files, one map per line:

- CTF: `config/ctf-mapcycle.txt`
- Rocket Arena: `config/ra-mapcycle.txt`

CTF defaults to `e1m2`, `e1m3`, `e1m5`. Rocket Arena defaults to `arena3`,
`arena5`: compact purpose-built arenas rather than episode maps. Both rotate
sequentially after a randomly selected starting map. Set `CTF_START_MAP` or `RA_START_MAP` for a fixed start.
Set `CTF_MAPCYCLE_RANDOM=1` or `RA_MAPCYCLE_RANDOM=1` for randomized rotation.
Restart the affected service after changing a rotation file. Missing maps or CTF
flag definitions cause a clear startup error.

Configure `.env` as needed:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CTF_PORT` / `RA_PORT` | `27505` / `27506` | Host UDP ports |
| `CTF_TIMELIMIT` / `RA_TIMELIMIT` | `10` / `10` | Minutes per map/match |
| `CTF_FRAGLIMIT` / `RA_FRAGLIMIT` | `0` / `10` | Frag limits; 0 disables |
| `QW_CTF_HOOK` / `QW_CTF_RUNES` | `1` / `1` | Enable hook/runes; 0 disables |
| `QW_RCON_PASSWORD` | empty | Remote console password |
| `QW_ADMIN_PASSWORD` | empty | KTX in-game admin password |

Re-run `docker compose up -d` with the same profiles and Compose file after editing
`.env`, so containers are recreated with the new values. For RCON in ezQuake,
set `cl_crypt_rcon 1` and your `rcon_password`; in-game admin login uses
`admin <password>`.

To stream both servers, enable the `qtv` profile and set
`QTV_SOURCES=ctf:27500 ra:27500` in `.env`. Include your other game services in
that list if needed. See the [configuration reference](docs/CONFIGURATION.md#ctf-and-rocket-arena)
for custom maps, flag definitions, secret files and per-server credentials.
