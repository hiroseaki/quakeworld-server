#!/usr/bin/env python3
"""Fetch the selected arena BSPs for local use; never add them to the image."""
import hashlib
from pathlib import Path
import sys
import subprocess

MAPS = {
    'arena3.bsp': '6758786d6cae488aa73c0bc616ae75f350fa66e469bc6580880fb872b4dbf90e',
    'arena5.bsp': 'cf2f3a7a284c6fb0237c1fb9e1f61d6a918f75d62aed815387a0df5b315e6b02',
}
BASE = 'https://quakeworld.fi/nquake/sv-maps/qw/maps/'


def main():
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'data/maps'
    dest.mkdir(parents=True, exist_ok=True)
    for name, expected in MAPS.items():
        target = dest / name
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                sys.exit(f'{target} differs from the pinned map; move it aside to install this version')
            print(f'{name}: verified existing file')
            continue
        data = subprocess.check_output(['curl', '--fail', '--silent', '--show-error',
                                        '--location', '--retry', '3', '--max-time', '60', BASE + name])
        if hashlib.sha256(data).hexdigest() != expected:
            sys.exit(f'{name}: checksum mismatch; file not installed')
        # Exclusive creation preserves user files if another installer raced us.
        with target.open('xb') as output:
            output.write(data)
        target.chmod(0o644)
        print(f'{name}: installed in {dest}')


if __name__ == '__main__':
    main()
