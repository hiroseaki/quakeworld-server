#!/bin/sh
# Download the original complete shareware distribution for LOCAL use / CI only.
# Retain the original archive and its license alongside the extracted data.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
dest=${1:-$root/.cache/quake-shareware}
mkdir -p "$dest"
dest=$(CDPATH= cd -- "$dest" && pwd)
archive="$dest/quake106.zip"
if [ ! -f "$archive" ]; then
  curl --fail --location --retry 3 --max-time 120 \
    https://www.gamers.org/pub/idgames/idstuff/quake/quake106.zip -o "$archive.tmp"
  mv "$archive.tmp" "$archive"
fi
python3 - "$archive" <<'PY'
import hashlib, pathlib, sys, zipfile
archive = pathlib.Path(sys.argv[1])
expected = 'ec6c9d34b1ae0252ac0066045b6611a7919c2a0d78a3a66d9387a8f597553239'
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    sys.exit('Shareware archive checksum mismatch')
with zipfile.ZipFile(archive) as z:
    (archive.parent / 'resource.1').write_bytes(z.read('resource.1'))
PY
# libarchive's bsdtar or lhasa can read the self-extracting LHA without executing it.
if command -v lha >/dev/null 2>&1; then
  (cd "$dest" && lha xfq resource.1)
else
  (cd "$dest" && tar -xf resource.1)
fi
python3 - "$dest" <<'PY'
from pathlib import Path
import shutil, sys
root = Path(sys.argv[1])
# Normalize actual directory entries too (macOS may use a case-insensitive FS).
for directory in list(root.iterdir()):
    if directory.is_dir() and directory.name.lower() == 'id1' and directory.name != 'id1':
        temporary = root / '.id1-normalize'
        directory.rename(temporary)
        temporary.rename(root / 'id1')
target = root / 'id1'
target.mkdir(exist_ok=True)
for file in list(root.rglob('*')):
    if file.is_file() and file.name.lower() == 'pak0.pak' and file != target / 'pak0.pak':
        output = target / 'pak0.pak'
        if output.exists() and file.samefile(output):
            temporary = target / '.pak0-normalize'
            file.rename(temporary)
            temporary.rename(output)
        else:
            shutil.copyfile(file, output)
if not (target / 'pak0.pak').is_file():
    sys.exit('Extraction failed; install lhasa or libarchive-tools')
# LHA can restore owner-only DOS-era permissions on Linux. The container
# reads this non-secret game data as UID 10001 through a read-only bind mount.
target.chmod(0o755)
(target / 'pak0.pak').chmod(0o644)
PY
printf 'Shareware extracted locally. License: %s/slicnse.txt (may be uppercase).\n' "$dest"
printf 'For tests: QUAKE_PAK_DIR=%s/id1 make smoke\n' "$dest"
