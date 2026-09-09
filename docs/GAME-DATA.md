# Game data and maps

This repository and its image do not redistribute Quake game data.

## Required files

Mount a directory containing lowercase `pak0.pak` and `pak1.pak` at `/nquake/id1`.
Compose defaults to `pak_files/`; change `QW_PAK_DIR` to use another location,
including the previous `./data/id1` path. Both PAKs are required for the supplied
`dm2`, `dm3`, `dm4`, `dm6` rotation and the match default `dm3`.

For shareware-only use, select episode-one maps such as `e1m2` and `e1m3` in the
FFA rotation and set `QW_START_MAP=e1m2` for match servers. `dm1` is not included
in shareware. Startup validates PAK directory structures and map availability.

Optional local helper:

```sh
./scripts/fetch-shareware.sh
```

Requires Python 3, curl, and lhasa or libarchive tar. It downloads the original
complete Quake 1.06 archive, verifies its SHA-256, and extracts locally while
retaining the original archive and license in ignored `.cache/quake-shareware`.
It never adds game data to the Docker build or to Git. CI uses this same local
extraction for tests and does not upload the PAKs as artifacts.

## Shareware distribution terms

Shareware is not a blanket permission to redistribute individual data files.
Section 6 of the original license grants end users free distribution of the
software **as a whole**, with the agreement accompanying it. We have not found a
permission there to bundle only extracted `pak0.pak` in a public image.

- [Original shareware license, mirrored by Gentoo](https://chromium.googlesource.com/external/github.com/gentoo/gentoo/+/92cfd03cca7f8af34145ba1cd6276cc95a5d1ce0/licenses/quake1-demodata)
- [id Software: game data remains under its original terms](https://github.com/id-Software/Quake/blob/master/readme.txt)

Users provide `pak1.pak` from their licensed copy. Other projects distributing data
are not evidence of permission for this project.

## Custom maps

Put loose `example.bsp` and optional `example.ent` files in `data/maps/`, then add
`example` to `config/mapcycle.txt`. Location files go in `data/locs/`. Blank lines
and comment lines beginning with `#` are ignored. Map files do not require an
image rebuild, but recreate the container after changing its startup rotation.
Community assets have their own terms; obtain permission before redistributing.
