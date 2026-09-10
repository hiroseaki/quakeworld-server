#!/usr/bin/env python3
"""Generate private runtime configuration, then replace this process with its service."""
import json
import os
from pathlib import Path
import re
import secrets
import struct
import sys

RUNTIME = Path('/nquake/ktx/runtime')
MASTERS = 'master.quakeworld.nu:27000 master.quakeservers.net:27000 qwmaster.fodquake.net:27000'


def text(name, default=''):
    value = os.environ.get(name, default)
    if any(ord(c) < 32 or ord(c) == 127 or c in '\\";$' for c in value):
        raise ValueError(f'{name} contains unsupported configuration characters')
    return value


def password(name, alias=None):
    file = os.environ.get(name + '_FILE')
    if not file and alias:
        file = os.environ.get(alias + '_FILE')
    if file:
        # Explicit file failures must never silently fall back to another password.
        value = Path(file).read_text().rstrip('\r\n')
        if any(ord(c) < 32 or ord(c) == 127 or c in '\\";$' for c in value):
            raise ValueError(f'{name}_FILE contains unsupported configuration characters')
        return value
    return text(name, text(alias) if alias else '')


def number(name, default, low=0, high=2147483647):
    value = os.environ.get(name, str(default))
    if not re.fullmatch(r'[0-9]{1,10}', value) or not low <= int(value) <= high:
        raise ValueError(f'{name} must be an integer between {low} and {high}')
    return int(value)


def address(value):
    if not re.fullmatch(r'[a-zA-Z0-9._\[\]:-]+', value):
        raise ValueError('invalid server address')
    return value


def write(name, lines):
    (RUNTIME / name).write_text('\n'.join(lines) + '\n')


def custom(service):
    path = Path(os.environ.get('QW_CONFIG_FILE', f'/config/local-{service}.cfg'))
    if 'QW_CONFIG_FILE' in os.environ or path.exists():
        (RUNTIME / 'custom.cfg').write_text(path.read_text())
    else:
        write('custom.cfg', ['// No local overrides.'])


def pak_maps(directory):
    """Validate PAK directories and find available BSPs without extracting game data."""
    maps = set()
    pak0 = directory / 'pak0.pak'
    if not pak0.is_file():
        raise ValueError(f'missing {pak0}; mount your legally obtained Quake data')
    for pak in sorted(directory.glob('pak*.pak')):
        with pak.open('rb') as f:
            header = f.read(12)
            if len(header) != 12:
                raise ValueError(f'invalid PAK header: {pak.name}')
            magic, offset, length = struct.unpack('<4sII', header)
            size = pak.stat().st_size
            if magic != b'PACK' or length % 64 or offset < 12 or offset + length > size:
                raise ValueError(f'invalid PAK directory: {pak.name}')
            f.seek(offset)
            for _ in range(length // 64):
                raw, start, count = struct.unpack('<56sII', f.read(64))
                if start + count > size:
                    raise ValueError(f'invalid PAK entry: {pak.name}')
                name = raw.split(b'\0', 1)[0].decode('ascii')
                if name.startswith('maps/') and name.endswith('.bsp'):
                    maps.add(name[5:-4])
    return maps


def game_resource(relative, root):
    """Read a loose file or PAK entry in MVDSV's game-directory priority order."""
    for game in ('ktx', 'qw', 'id1'):
        directory = root / game
        # MVDSV places numbered packs ahead of loose files within each directory.
        packs = sorted(directory.glob('pak[0-9]*.pak'),
                       key=lambda p: int(p.stem[3:]) if p.stem[3:].isdigit() else -1,
                       reverse=True)
        for pak in packs:
            with pak.open('rb') as f:
                header = f.read(12)
                if len(header) != 12:
                    raise ValueError(f'invalid PAK header: {pak.name}')
                magic, offset, length = struct.unpack('<4sII', header)
                if magic != b'PACK' or offset < 12 or length % 64 or offset + length > pak.stat().st_size:
                    raise ValueError(f'invalid PAK directory: {pak.name}')
                f.seek(offset)
                entries = f.read(length)
                for i in range(0, length, 64):
                    raw, start, count = struct.unpack('<56sII', entries[i:i+64])
                    if raw.split(b'\0', 1)[0] == relative.encode():
                        if start + count > pak.stat().st_size:
                            raise ValueError(f'invalid PAK entry: {pak.name}')
                        f.seek(start)
                        return f.read(count)
        path = directory / relative
        if path.is_file():
            return path.read_bytes()
    return None


def validate_ctf_map(name, root=Path('/nquake')):
    entities = game_resource(f'maps/ctf/{name}.ent', root)
    if entities is None:
        entities = game_resource(f'maps/{name}.ent', root)
    if entities is None:
        bsp = game_resource(f'maps/{name}.bsp', root)
        if bsp is None or len(bsp) < 124:
            raise ValueError(f'CTF map {name} has no readable BSP entity data')
        version, offset, length = struct.unpack('<iii', bsp[:12])
        if version != 29 or offset < 124 or length < 0 or offset + length > len(bsp):
            raise ValueError(f'CTF map {name} needs a Quake BSP or maps/ctf/{name}.ent')
        entities = bsp[offset:offset + length]
    # Comments must not masquerade as real flag definitions.
    entities = re.sub(r'//[^\n]*', '', entities.decode('latin1'))
    for team in (1, 2):
        if not re.search(r'"classname"\s+"item_flag_team' + str(team) + '"', entities):
            raise ValueError(f'CTF map {name} is missing team {team} flag; supply maps/ctf/{name}.ent')


def server():
    mode = text('QW_MODE', 'ffa')
    if mode not in ('ffa', 'ktx', 'ctf', 'ra'):
        raise ValueError('QW_MODE must be ffa, ktx, ctf or ra')
    default_mode = text('QW_DEFAULT_MODE', '1on1')
    if default_mode not in ('1on1', '2on2', '3on3', '4on4', '10on10', 'ffa'):
        raise ValueError('unsupported QW_DEFAULT_MODE')
    available = pak_maps(Path('/nquake/id1'))
    for directory in ('/nquake/qw/maps', '/nquake/ktx/maps', '/nquake/id1/maps'):
        available.update(p.stem for p in Path(directory).glob('*.bsp'))
    maps = []
    if mode != 'ktx':
        cycle = Path(os.environ.get('QW_MAPCYCLE_FILE', f'/etc/quakeworld/{mode}-mapcycle.txt'))
        maps = [line.strip() for line in cycle.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
        if len(maps) > 1000:
            raise ValueError('map cycle supports at most 1000 entries')
        if not maps:
            raise ValueError('map cycle is empty')
    start = text('QW_START_MAP')
    if not start:
        if mode != 'ktx':
            last = Path('/nquake/logs/.last-start-map')
            previous = last.read_text().strip() if last.exists() else ''
            choices = [m for m in maps if m != previous] or maps
            start = secrets.choice(choices)
        else:
            start = 'dm3'
    for m in maps + [start]:
        if not re.fullmatch(r'[a-zA-Z0-9_+-]+', m) or m not in available:
            raise ValueError(f'map {m!r} is unavailable; supply pak1.pak or a loose BSP, or change the map selection')
    if mode == 'ctf':
        for m in set(maps + [start]):
            validate_ctf_map(m)
    for directory in ('/nquake/logs', '/nquake/ktx/demos'):
        p = Path(directory) / '.write-test'
        try:
            p.write_text('')
            p.unlink()
        except OSError as e:
            raise ValueError(f'{directory} must be writable by UID {os.getuid()}') from e
    Path('/nquake/logs/.last-start-map').write_text(start + '\n')
    port = number('QW_PORT', 27500, 1, 65535)
    masters = text('QW_MASTER_SERVERS', MASTERS)
    for master in masters.split():
        address(master)
    qtv_pass = password('QW_QTV_PASSWORD')
    qtv_enabled = number('QW_QTV_ENABLED', 0, 0, 1)
    write('mode.cfg', [
        f'set k_matchless {1 if mode in ("ffa", "ctf") else 0}',
        'set k_use_matchless_dir 0',
        f'set k_defmode {"ffa" if mode in ("ffa", "ctf") else "1on1" if mode == "ra" else default_mode}',
        f'set k_allowed_free_modes {96 if mode == "ctf" else 1 if mode == "ra" else 32 if mode == "ffa" else 63}',
        'set k_autoreset 0', 'set k_matchless_countdown 0',
        f'set k_defmap "{start}"',
    ] + ([
        f'set k_mode {4 if mode == "ctf" else 1 if mode == "ra" else 3 if mode == "ffa" else 1}',
        f'set k_rocketarena {1 if mode == "ra" else 0}',
        f'sv_loadentfiles {1 if mode == "ctf" else 0}',
        f'sv_loadentfiles_dir "{"ctf" if mode == "ctf" else ""}"',
    ] if mode != 'ktx' else []))
    settings = [
        f'hostname "{text("QW_HOSTNAME", "QuakeWorld " + mode.upper())}"',
        f'sv_admininfo "{text("QW_ADMININFO")}"',
        f'maxclients {number("QW_MAXCLIENTS", 16, 1, 32)}',
        f'maxspectators {number("QW_MAXSPECTATORS", 8, 0, 32)}',
        f'set countrycode "{text("QW_COUNTRYCODE")}"',
        f'set city "{text("QW_CITY")}"',
        f'set coords "{text("QW_COORDS")}"',
        f'setmaster {masters if masters else "clear"}',
        'qtv_maxstreams 1',
        f'qtv_streamport {port if qtv_enabled else 0}',
        f'sv_demoMaxDirSize {number("QW_DEMO_MAX_MB", 1024, 1, 1048576) * 1024}',
        f'sv_demoMaxSize {number("QW_DEMO_FILE_MAX_MB", 64, 1, 1024) * 1024}',
        'sv_demoClearOld 10',
    ]
    if mode != 'ktx':
        settings += [f'timelimit {number("QW_TIMELIMIT", 10, 0, 1440)}',
                     f'fraglimit {number("QW_FRAGLIMIT", 0 if mode == "ctf" else 10 if mode == "ra" else 50, 0, 100000)}']
    if mode == 'ctf':
        settings += ['teamplay 4', 'set k_ctf_custom_models 0',
                     f'set k_ctf_hook {number("QW_CTF_HOOK", 1, 0, 1)}',
                     f'set k_ctf_runes {number("QW_CTF_RUNES", 1, 0, 1)}',
                     'set k_ctf_based_spawn 1', 'set k_lockmin 0', 'set k_lockmax 32',
                     'set k_membercount 0', 'set k_no_vote_map 0']
    elif mode == 'ra':
        settings += ['samelevel 0', 'teamplay 0', 'set k_lockmode 0', 'set k_exclusive 0']
    write('server.cfg', settings)
    admin_pass = password('QW_ADMIN_PASSWORD')
    if admin_pass == 'none':
        raise ValueError('QW_ADMIN_PASSWORD cannot be the reserved KTX value none')
    write('passwords.cfg', [
        f'rcon_password "{password("QW_RCON_PASSWORD", "RCON_PASSWORD")}"',
        f'set k_admins {1 if admin_pass else 0}',
        f'set k_admincode "{admin_pass}"',
        f'password "{password("QW_PASSWORD")}"',
        f'spectator_password "{password("QW_SPECTATOR_PASSWORD")}"',
        f'qtv_password "{qtv_pass}"',
    ])
    write('mapcycle.cfg', [f'set k_random_maplist {number("QW_MAPCYCLE_RANDOM", 1 if mode == "ffa" else 0, 0, 1)}'] +
          [f'set k_ml_{i} "{m}"' for i, m in enumerate(maps)])
    write('arena.cfg', ['exec runtime/mode.cfg', 'exec runtime/server.cfg',
                        'exec runtime/mapcycle.cfg', 'exec runtime/custom.cfg',
                        'exec runtime/passwords.cfg'] if mode == 'ra' else [])
    args = ['/nquake/mvdsv', '-port', str(port), '-mem',
            str(number('QW_MEMORY_MB', 128, 32, 4096)), '-game', 'ktx',
            '+map', start]
    return args


def qwfwd():
    masters = text('QW_MASTER_SERVERS', MASTERS)
    for master in masters.split():
        address(master)
    write('qwfwd.cfg', [
        f'set net_port {number("QWFWD_PORT", 30000, 1, 65535)}',
        'set net_ip 0.0.0.0',
        f'set hostname "{text("QWFWD_HOSTNAME", "QuakeWorld proxy")}"',
        f'set hostport "{text("QWFWD_PUBLIC_ADDRESS")}"',
        f'set countrycode "{text("QW_COUNTRYCODE")}"',
        f'set city "{text("QW_CITY")}"',
        f'set coords "{text("QW_COORDS")}"',
        f'set masters "{masters}"',
        f'set masters_heartbeat {1 if masters else 0}',
        f'set masters_query {1 if masters else 0}',
        'exec custom.cfg',
    ])
    os.chdir(RUNTIME)
    return ['/usr/local/bin/qwfwd']


def qtv():
    (RUNTIME / 'demos').mkdir(exist_ok=True)
    lines = [
        f'listen_address ":{number("QTV_PORT", 28000, 1, 65535)}"',
        f'hostname "{text("QTV_HOSTNAME", "QuakeWorld TV")}"',
        f'address "{text("QTV_PUBLIC_ADDRESS")}"',
        f'qtv_password "{password("QTV_PASSWORD")}"',
        f'maxclients {number("QTV_MAXCLIENTS", 100, 1, 10000)}',
        f'parse_delay {number("QTV_DELAY", 10, 0, 3600)}',
        f'masters "{text("QW_MASTER_SERVERS", MASTERS)}"',
        'http_upload_enabled 0',
        'allow_download 0',
        'log_pretty 0',
        'exec custom.cfg',
    ]
    sources = os.environ.get('QTV_SOURCES_FILE')
    if sources:
        entries = json.loads(Path(sources).read_text())
        if not isinstance(entries, list):
            raise ValueError('QTV_SOURCES_FILE must contain a JSON array')
    else:
        entries = [{'address': a} for a in text('QTV_SOURCES').split()]
    shared = password('QW_QTV_PASSWORD')
    for entry in entries:
        target = address(entry['address'])
        secret = Path(entry['password_file']).read_text().rstrip('\r\n') if 'password_file' in entry else entry.get('password', shared)
        if any(ord(c) < 32 or ord(c) == 127 or c in '\\";$' for c in secret):
            raise ValueError('invalid source password')
        lines.append(f'qtv "{target}" "{secret}"')
    write('qtv.cfg', lines)
    os.chdir(RUNTIME)
    return ['/usr/local/bin/qtv']


def main():
    if len(sys.argv) > 1:
        os.execvp(sys.argv[1], sys.argv[1:])
    os.umask(0o077)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    service = text('QW_SERVICE', 'server')
    if service not in ('server', 'qwfwd', 'qtv'):
        raise ValueError('QW_SERVICE must be server, qwfwd or qtv')
    custom(service)
    args = {'server': server, 'qwfwd': qwfwd, 'qtv': qtv}[service]()
    print(f'Starting {service}', flush=True)
    os.execv(args[0], args)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Do not echo values from configs or credentials in exceptions.
        if isinstance(exc, json.JSONDecodeError):
            detail = 'invalid JSON in QTV_SOURCES_FILE'
        else:
            detail = str(exc)
        sys.exit(f'quakeworld: {detail}')
