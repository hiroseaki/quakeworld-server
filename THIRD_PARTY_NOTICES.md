# Third-party notices

| Component | Source | License |
| --- | --- | --- |
| MVDSV | https://github.com/QW-Group/mvdsv | GPL-2.0 |
| KTX | https://github.com/QW-Group/ktx | GPL-2.0 |
| qwfwd | https://github.com/QW-Group/qwfwd | GPL-2.0 |
| QTV (Go implementation) | https://github.com/QW-Group/qtv | BSD-2-Clause |

Exact commits are pinned in Dockerfile. Corresponding source, original notices,
and licenses are distributed under `/usr/src/quakeworld` in the image, including
MVDSV's source submodule and QTV's vendored Go dependencies with their licenses.
`SOURCE-COMMITS` in that directory records the C components; QTV has its own
`qtv/SOURCE-COMMITS`. The project Dockerfile records build commands. Container glue
is MIT; its license is included under `/usr/share/doc/quakeworld`.

Debian runtime packages retain their upstream licenses under `/usr/share/doc`.
The OCI license label describes the main components, not an exhaustive inventory
of all Debian and vendored dependency licenses.

Quake, QuakeWorld, and related names/game data belong to their respective owners.
No Quake PAK files are included in the image or repository.

The image includes the unmodified `arena3.bsp` and `arena5.bsp` community maps
from https://quakeworld.fi/nquake/sv-maps/qw/maps/. Their download URLs and exact
SHA-256 hashes are recorded in `container/fetch-ra-maps.py` under the bundled
source directory. The matching `.ent` definitions come from the pinned KTX
source. Map assets retain their original ownership; the container glue's MIT
license does not relicense these assets.
