#!/usr/bin/env python3
"""Resolve upstream releases to exact commits; optionally update Dockerfile pins."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def api(path):
    headers = {'Accept': 'application/vnd.github+json'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    request = urllib.request.Request('https://api.github.com/repos/QW-Group/' + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'Dockerfile'
    original = updated = path.read_text()
    print('Update pinned upstream components to the following revisions.\n')
    print('| Component | Current | Proposed |\n| --- | --- | --- |')
    for repo in ('mvdsv', 'ktx', 'qwfwd', 'qtv'):
        prefix = repo.upper()
        current = re.search(rf'^ARG {prefix}_COMMIT=(\w+)$', original, re.M).group(1)
        # MVDSV follows development; QTV has no releases. Both remain commit-pinned.
        if repo in ('mvdsv', 'qtv'):
            ref = api(repo)['default_branch']
        else:
            ref = api(repo + '/releases/latest')['tag_name']
        commit = api(repo + '/commits/' + ref)['sha']
        if not re.fullmatch('[0-9a-f]{40}', commit):
            raise ValueError('invalid upstream commit')
        updated = re.sub(rf'^ARG {prefix}_COMMIT=.*$', f'ARG {prefix}_COMMIT={commit}', updated, flags=re.M)
        if repo != 'qtv':
            if repo == 'mvdsv':
                header = api(f'mvdsv/contents/src/version.h?ref={commit}')
                source = base64.b64decode(header['content'], validate=False).decode('utf-8')
                match = re.search(r'^#define\s+SERVER_VERSION\s+"([^"]+)"', source, re.M)
                if not match:
                    raise ValueError('MVDSV SERVER_VERSION not found at selected commit')
                version = match.group(1)
            else:
                version = ref.removeprefix('v')
            if not re.fullmatch(r'[0-9][0-9A-Za-z.+-]*', version):
                raise ValueError('unsupported upstream version')
            updated = re.sub(rf'^ARG {prefix}_VERSION=.*$', f'ARG {prefix}_VERSION={version}', updated, flags=re.M)
        print(f'| {repo} | `{current[:12]}` | [{ref}: {commit[:12]}](https://github.com/QW-Group/{repo}/commit/{commit}) |')
    changed = updated != original
    if args.write and changed:
        path.write_text(updated)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write(f'changed={str(changed).lower()}\n')
    print('\nReview release notes and run the Docker workflow on this branch before merging. No image is published by this update.')
    return 0 if args.write or not changed else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f'Upstream lookup failed: {exc}')
