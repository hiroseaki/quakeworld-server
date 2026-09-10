# QuakeWorld Server Docker

One image for MVDSV/KTX **FFA, CTF, Rocket Arena and match servers**, **QTV**, and **qwfwd**.
Run one process per container. The supplied Compose file can start one FFA,
four match servers, a shared QTV, and a proxy with a single command.

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
After publication, use the registry Compose file from the repository root:

```sh
export QW_IMAGE=ghcr.io/hiroseaki/quakeworld-server:0.1.0
COMPOSE_PROFILES=ffa,ktx,qtv,proxy docker compose \
  --project-directory . -f examples/compose.registry.yaml up -d
```

## Verification

```sh
make check
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

## CTF and Rocket Arena (next version)

Build and start either or both profiles:

```sh
COMPOSE_PROFILES=ctf,ra docker compose up -d --build
```

CTF listens on UDP 27505; Rocket Arena on UDP 27506. Edit
`config/ctf-mapcycle.txt` and `config/ra-mapcycle.txt` for separate map rotations.
The defaults use shareware maps. See [configuration](docs/CONFIGURATION.md#ctf-and-rocket-arena)
for gameplay, map requirements, passwords and QTV setup. These profiles require
the new build; the published `0.1.0` image does not include them.
