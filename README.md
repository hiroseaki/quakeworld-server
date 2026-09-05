# QuakeWorld Server Docker

A reproducible, multi-architecture Docker image for a modern QuakeWorld FFA
server powered by [MVDSV](https://github.com/QW-Group/mvdsv) and
[KTX](https://github.com/QW-Group/ktx).

The image is deliberately **BYO game data**. It contains no Quake PAK files,
commercial maps, or community map packs. You supply game data that you are
licensed to use at runtime.

## What is included

- MVDSV 1.11 and KTX 1.47, built from pinned commits
- `linux/amd64` and `linux/arm64` build support
- non-root runtime, dropped capabilities, read-only-root support
- Docker health check using the QuakeWorld UDP status protocol
- random startup map without repeating the previous startup map
- environment-based FFA settings and Docker-secret support for RCON
- persistent logs and demos; bind-mounted maps and location files
- corresponding MVDSV/KTX source under `/usr/src/quakeworld` in the image

## Quick start from source

Requirements: Docker Engine with Compose, OpenSSL, and your legally obtained
Quake `pak0.pak` (plus `pak1.pak` for the complete registered map set).

```sh
make setup
cp /path/to/pak0.pak data/id1/pak0.pak
cp /path/to/pak1.pak data/id1/pak1.pak  # recommended
make up
make logs
```

The default server listens on UDP port `27500`. Copy `.env.example` to `.env`
and change the values there. Edit `config/mapcycle.txt` to select maps.

To connect locally from a QuakeWorld client:

```text
connect 127.0.0.1:27500
```

## Run a published image

Copy [`examples/compose.registry.yaml`](examples/compose.registry.yaml), create
the listed data/config directories, and set `QW_IMAGE` to the GHCR or Docker Hub
image name. The repository intentionally has no real registry owner hard-coded
before its first publication.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `QW_HOSTNAME` | `QuakeWorld FFA` | Name shown in server browsers |
| `QW_PORT` | `27500` | UDP listen and published port |
| `QW_MAXCLIENTS` | `16` | Maximum players (1–32) |
| `QW_MAXSPECTATORS` | `8` | Maximum spectators |
| `QW_TIMELIMIT` | `10` | Map time in minutes |
| `QW_FRAGLIMIT` | `50` | Frag limit; `0` disables it |
| `QW_START_MAP` | random | Fixed startup map when set |
| `QW_MAPCYCLE_FILE` | `/config/mapcycle.txt` | Map list inside the container |
| `QW_MEMORY_MB` | `128` | MVDSV zone memory |
| `QW_COUNTRYCODE`, `QW_CITY`, `QW_COORDS` | empty | Server-browser metadata |
| `QW_ADMININFO` | empty | Public administrator contact |
| `QW_MASTER_SERVERS` | common QW masters | Space-separated master list |
| `RCON_PASSWORD_FILE` | `/run/secrets/rcon_password` | RCON Docker secret path |

`RCON_PASSWORD` is accepted as a fallback, but a secret file is preferred.

## Maps and game data

See [Game data and maps](docs/GAME-DATA.md). Map files are mounted from
`data/maps`, so adding a `.bsp` does not require rebuilding the image.

## Publishing

The workflows build on pull requests and publish version tags to GHCR. Docker
Hub publishing is enabled by adding a repository variable and two secrets. See
[Publishing](docs/PUBLISHING.md).

## Security

Only UDP `27500` needs to be exposed. Do not expose RCON passwords through Git,
Compose files, or image layers. See [SECURITY.md](SECURITY.md).

## Licenses

The container glue in this repository is MIT licensed. MVDSV and KTX are
GPL-2.0 software; their licenses, notices, pinned revisions, and corresponding
source remain with the distributed image. Quake game data is not included.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
