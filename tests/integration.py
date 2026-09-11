#!/usr/bin/env python3
"""Exercise the built image in isolated containers; never publish game data or ports."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGE = sys.argv[1] if len(sys.argv) > 1 else 'quakeworld-server:test'
PAK = Path(os.environ.get('QUAKE_PAK_DIR', str(ROOT / 'pak_files'))).resolve()
RUN = 'qw-test-' + uuid.uuid4().hex[:10]
containers = []


def docker(*args, check=True):
    return subprocess.run(['docker', *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check, timeout=120)


def inside(name, code):
    result = docker('exec', name, 'python3', '-c', code, check=False)
    if result.returncode:
        raise AssertionError(result.stderr + result.stdout)
    return result.stdout


def start(role, name, extra=(), mode='ffa'):
    container = RUN + '-' + name
    containers.append(container)
    docker('run', '-d', '--name', container, '--network', RUN, '--network-alias', name,
           '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
           '--tmpfs', '/nquake/ktx/runtime:uid=10001,gid=10001,mode=0700',
           '--tmpfs', '/tmp:uid=10001,gid=10001,mode=0700',
           '--tmpfs', '/nquake/logs:uid=10001,gid=10001,mode=0700',
           '--tmpfs', '/nquake/ktx/demos:uid=10001,gid=10001,mode=0700',
           '-e', 'QW_MASTER_SERVERS=', '-e', 'QW_SERVICE=' + role,
           '-e', 'QW_MODE=' + mode, '-e', 'QW_HOSTNAME=' + name,
           '-e', 'QW_START_MAP=' + ('arena3' if mode == 'ra' else 'e1m2'), '-e', 'QW_TIMELIMIT=13',
           '-e', 'QW_RCON_PASSWORD=integration-rcon', '-e', 'QW_ADMIN_PASSWORD=integration-admin',
           '-e', 'QW_QTV_ENABLED=1', '-e', 'QW_QTV_PASSWORD=integration-stream',
           '-v', str(work / 'empty-maps') + ':/nquake/qw/maps:ro',
           '-v', str(PAK) + ':/nquake/id1:ro',
           '-v', str(work) + ':/test:ro', '-e', 'QW_MAPCYCLE_FILE=' + ('/etc/quakeworld/ra-mapcycle.txt' if mode == 'ra' else '/test/maps.txt'),
           *extra, IMAGE)
    return container


def healthy(name):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        result = docker('exec', name, 'python3', '/usr/local/lib/quakeworld/healthcheck.py', check=False)
        if result.returncode == 0:
            return
        if docker('inspect', '-f', '{{.State.Running}}', name).stdout.strip() != 'true':
            break
        time.sleep(0.5)
    raise AssertionError(f'{name} did not become healthy')


def rcon(name, command):
    # Short-lived loopback socket; output checked in memory and never prints passwords.
    time.sleep(1.1)
    return inside(name, f'''import socket, hashlib, struct, time
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.settimeout(3)
s.connect(('127.0.0.1',27500))
stamp=struct.pack('<Q',int(time.time())).hex()
command={command!r}
digest=hashlib.sha1(('rcon integration-rcon'+stamp+' '+' '.join(command.split())+' ').encode()).hexdigest().upper()
s.send(b'\\xff'*4 + ('rcon '+digest+stamp+' '+command+'\\n').encode())
print(s.recv(65535).decode('latin1'))
''')


if not (PAK / 'pak0.pak').is_file():
    sys.exit('Set QUAKE_PAK_DIR to a directory containing legally obtained pak0.pak (pak1.pak optional).')

with tempfile.TemporaryDirectory(prefix=RUN) as directory:
    work = Path(directory)
    # Host bind paths are made readable explicitly, including on native Linux.
    work.chmod(0o755)
    (work / 'empty-maps').mkdir(mode=0o755)
    (work / 'maps.txt').write_text('e1m2\ne1m3\n')
    (work / 'maps.txt').chmod(0o644)
    for filename, value in [('rcon', 'integration-rcon'), ('admin', 'integration-admin'), ('stream4', 'integration-stream4')]:
        (work / filename).write_text(value + '\n')
        (work / filename).chmod(0o644)
    sources = [{'address': f'{name}:27500'} for name in ('ffa', 'ktx-1', 'ktx-2', 'ktx-3', 'ktx-4', 'ctf', 'ra')]
    sources[4]['password_file'] = '/test/stream4'
    (work / 'sources.json').write_text(json.dumps(sources))
    (work / 'sources.json').chmod(0o644)
    docker('network', 'create', '--internal', RUN)
    try:
        ffa = start('server', 'ffa')
        matches = [start('server', f'ktx-{i}', ['-e', f'QW_DEFAULT_MODE={mode}'] + (['-e', 'QW_RCON_PASSWORD=wrong-env', '-e', 'QW_RCON_PASSWORD_FILE=/test/rcon', '-e', 'QW_ADMIN_PASSWORD_FILE=/test/admin'] if i == 2 else []) + (['-e', 'QW_QTV_PASSWORD=integration-stream4'] if i == 4 else []), mode='ktx')
                   for i, mode in enumerate(('1on1', '1on1', '2on2', '4on4'), 1)]
        ctf = start('server', 'ctf', mode='ctf')
        ra = start('server', 'ra', mode='ra')
        qtv = start('qtv', 'qtv', ['-e', 'QTV_SOURCES=ffa:27500 ktx-1:27500 ktx-2:27500 ktx-3:27500 ktx-4:27500', '-e', 'QTV_DELAY=0', '-e', 'QTV_SOURCES_FILE=/test/sources.json'])
        proxy = start('qwfwd', 'proxy')
        for name in containers:
            healthy(name)
        inside(ra, "from pathlib import Path; assert not list(Path('/nquake/qw/maps').iterdir()); assert all(Path('/nquake/ktx/maps', m + '.bsp').is_file() for m in ('arena3', 'arena5'))")
        print('Bundled arenas are available with an empty read-only custom-map mount and no Internet access.', flush=True)
        rcon(ra, 'developer 1')
        print('All nine services respond to their protocol health checks.', flush=True)
        for name, expected in zip(matches, ('1', '1', '2', '2')):
            assert f'"k_mode" is "{expected}"' in rcon(name, 'k_mode')
        for name in [ffa, *matches, ctf, ra]:
            assert inside(name, 'import os; print(os.getuid())').strip() == '10001'
            assert 'Permission denied' not in docker('logs', name).stdout
        for name, matchless, default_mode in [(n, '1', 'ffa') for n in (ffa, ctf)] + [(ra, '0', '1on1')] + list(zip(matches, ['0']*4, ('1on1','1on1','2on2','4on4'))):
            for command in ('exec configs/reset.cfg', 'map arena5' if name == ra else 'map e1m3', 'exec configs/reset.cfg'):
                rcon(name, command)
            output = rcon(name, 'k_matchless')
            assert f'"k_matchless" is "{matchless}"' in output, output
            output = rcon(name, 'k_defmode')
            assert f'"k_defmode" is "{default_mode}"' in output, output
            inside(name, "from pathlib import Path; assert 'integration-admin' in Path('/nquake/ktx/runtime/passwords.cfg').read_text()")
            assert 'reset-ok' in rcon(name, 'echo reset-ok'), 'RCON not preserved'
        assert '"timelimit" is "13"' in rcon(ffa, 'timelimit')
        assert '"timelimit" is "13"' not in rcon(matches[0], 'timelimit'), 'FFA limits leaked into match mode'
        print('Modes, admin credentials and RCON survive reset and map changes.', flush=True)
        for name in (ffa, matches[0], ctf, ra):
            inside(name, (ROOT / 'tests/client_lifecycle.py').read_text())
            logs = docker('logs', name).stdout
            assert 'lifecycle-test' in logs and 'removed' in logs, 'client lifecycle not observed'
            assert 'alive-after-disconnect' in rcon(name, 'echo alive-after-disconnect')
        print('Real client join and last-player disconnect preserve RCON.', flush=True)

        for name, game_mode, arena in ((ctf, '4', '0'), (ra, '1', '1')):
            assert f'"k_mode" is "{game_mode}"' in rcon(name, 'k_mode')
            assert f'"k_rocketarena" is "{arena}"' in rcon(name, 'k_rocketarena')
            assert '"k_random_maplist" is "0"' in rcon(name, 'k_random_maplist')
            rcon(name, 'map arena3' if name == ra else 'map e1m2')
            companion = None
            if name == ra:
                code = (ROOT / 'tests/client_lifecycle.py').read_text().split("send('admin integration-admin')")[0]
                code = code.replace('12346', '12347').replace('lifecycle-test', 'arena-challenger')
                code += "send('ready')\ndeadline = time.monotonic() + 60\nwhile time.monotonic() < deadline:\n    send('pings')\n    receive()\n"
                companion = subprocess.Popen(['docker', 'exec', name, 'python3', '-c', code],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                inside(name, f'ROTATION_TEST = True\nARENA_TEST = {name == ra!r}\n' + (ROOT / 'tests/client_lifecycle.py').read_text())
                if name == ra:
                    logs = docker('logs', ra).stdout.lower()
                    assert 'the new winner' in logs and 'the new challenger' in logs, 'arena queue not exercised'
                    assert 'using entfile maps/ra/arena3.ent' in logs
                    assert 'using entfile maps/ra/arena5.ent' in logs
            finally:
                if companion is not None:
                    companion.terminate()
                    companion.wait(timeout=10)
            status = inside(name, "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(3); s.sendto(bytes([255])*4+b'status\\n',('127.0.0.1',27500)); print(s.recv(8192).decode('latin1'))")
            assert ('\\map\\arena5\\' if name == ra else '\\map\\e1m3\\') in status, 'rotation did not advance: ' + status
            assert f'"k_mode" is "{game_mode}"' in rcon(name, 'k_mode')
            assert f'"k_rocketarena" is "{arena}"' in rcon(name, 'k_rocketarena')
        print('CTF and Rocket Arena retain rules and advance their real map cycles.', flush=True)

        # QTV must actually receive upstream game data, not merely open a listening socket.
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            page = inside(qtv, "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:28000/nowplaying/').read().decode())")
            rows = re.findall(r'<td class="mn">(.*?)</td>', page, re.S)
            if len(rows) == 7 and all(re.search(r'e1m[23]|arena[35]', row) for row in rows) and all(f'ktx-{i}' in page for i in range(1,5)) and 'ffa' in page:
                break
            time.sleep(1)
        else:
            raise AssertionError('QTV did not list all seven live sources')
        print('QTV lists all seven game streams.', flush=True)
        # Open a real QW connection through qwfwd and forward RCON on that same socket.
        inside(qtv, r'''import socket, re, time
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.settimeout(5)
s.connect(('proxy',30000))
s.send(b'\xff'*4+b'getchallenge\n')
reply=s.recv(8192)
challenge=re.match(rb'\xff{4}c(-?\d+)',reply).group(1)
s.send(b'\xff'*4+b'connect 28 12345 '+challenge+b' "\\name\\proxy-test\\prx\\ffa:27500"\n')
reply=s.recv(8192)
assert reply.startswith(b'\xff'*4+b'j'), repr(reply)
time.sleep(1)
import hashlib,struct
stamp=struct.pack('<Q',int(time.time())).hex()
digest=hashlib.sha1(('rcon integration-rcon'+stamp+' echo forwarded-ok ').encode()).hexdigest().upper()
s.send(b'\xff'*4+('rcon '+digest+stamp+' echo forwarded-ok\n').encode())
while True:
    reply=s.recv(8192)
    if b'forwarded-ok' in reply: break
''')
        print('qwfwd forwards a real client connection and RCON traffic.', flush=True)
        for mode, selected, message in [('ctf', 'start', 'missing team 1 flag'),
                                        ('ra', 'missing_test_map', 'unavailable')]:
            invalid = start('server', 'invalid-' + mode, ['-e', 'QW_START_MAP=' + selected], mode=mode)
            deadline = time.monotonic() + 10
            while docker('inspect', '-f', '{{.State.Running}}', invalid).stdout.strip() == 'true':
                assert time.monotonic() < deadline, 'invalid map did not fail startup'
                time.sleep(0.1)
            assert docker('inspect', '-f', '{{.State.ExitCode}}', invalid).stdout.strip() == '1'
            logs = docker('logs', invalid)
            assert message in logs.stdout + logs.stderr
        print('Missing BSP and missing CTF flag fail startup clearly.', flush=True)
    except BaseException:
        for name in containers:
            result = docker('logs', '--tail', '35', name, check=False)
            # Only test credentials exist in these containers. Still redact them.
            logs = result.stdout + result.stderr
            for secret in ('integration-rcon', 'integration-admin', 'integration-stream'):
                logs = logs.replace(secret, '[redacted]')
            print(name + '\n' + logs, file=sys.stderr)
        raise
    finally:
        for name in containers:
            docker('rm', '-f', name, check=False)
        docker('network', 'rm', RUN, check=False)
print('Integration tests passed.')
