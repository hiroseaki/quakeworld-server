"""Minimal QW protocol client to exercise server-side join/admin/last-player reset.

Assets and rendering are deliberately skipped; this is a lifecycle smoke test,
not a replacement for playing a match with ezQuake.
"""
import re
import socket
import struct
import time

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(0.5)
s.connect(('127.0.0.1', 27500))
s.send(b'\xff'*4 + b'getchallenge\n')
challenge = re.match(rb'\xff{4}c(-?\d+)', s.recv(8192)).group(1)
s.send(b'\xff'*4 + b'connect 28 12346 ' + challenge + b' "\\name\\lifecycle-test\\team\\red\\rate\\10000"\n')
assert s.recv(8192).startswith(b'\xff'*4+b'j')
sequence = 0
ack = 0
reliable = 0
last = -1


def send(command):
    global sequence
    sequence = max(sequence + 1, ack + 1)
    s.send(struct.pack('<IIH', sequence, ack | (reliable << 31), 12346) + b'\x04' + command.encode() + b'\0')


def receive():
    global ack, reliable, last
    for attempt in range(10):
        try:
            data = s.recv(65535)
            break
        except socket.timeout:
            send('pings')
    else:
        raise AssertionError('no server reply')
    if data.startswith(b'\xff'*4):
        return b''
    seq, _ = struct.unpack('<II', data[:8])
    ack = seq & 0x7fffffff
    if ack > last:
        if seq >> 31:
            reliable ^= 1
        last = ack
    return data[8:]


send('new')
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    data = receive()
    if b'cmd pext' in data:
        send('pext')
        continue
    if b'cmd new' in data:
        send('new')
        continue
    # svc_serverdata, base protocol 28, spawn count; no extensions requested.
    index = data.find(b'\x0b\x1c\0\0\0')
    if index >= 0:
        count = struct.unpack('<I', data[index+5:index+9])[0]
        break
else:
    raise AssertionError('no QW serverdata')
send(f'spawn {count} 0')
receive()
send(f'begin {count}')
time.sleep(0.1)
send('admin integration-admin')
# Process outstanding signon data while waiting for the admin acknowledgement.
received = b''
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    received += receive()
    send('pings')
    # QW high-bit characters are normalized for message comparisons.
    plain = bytes(c & 127 for c in received).lower()
    if b'gains admins status' in plain:
        break
assert b'gains admins status' in plain, 'admin login failed'
if globals().get('ROTATION_TEST'):
    # Use the protocol's published checksum salt from the bundled upstream source.
    # Three delta usercmds, last one presses attack to leave the intermission.
    import binascii
    from pathlib import Path
    source = Path('/usr/src/quakeworld/mvdsv/src/common.c').read_text()
    initializer = source.split('static byte chktbl[1024] = {', 1)[1].split('}', 1)[0]
    table = bytes(int(v, 16) for v in re.findall(r'0x([0-9a-fA-F]+)', initializer)).ljust(1024, b'\0')
    time.sleep(2)
    send('forcestart' if globals().get('ARENA_TEST') else 'next_map')
    deadline = time.monotonic() + 45
    next_vote = time.monotonic() + 15 if globals().get('ARENA_TEST') else 0
    advanced = False
    while time.monotonic() < deadline:
        if time.monotonic() > next_vote:
            send('forcebreak' if globals().get('ARENA_TEST') else 'next_map')
            next_vote = time.monotonic() + 2
        sequence = max(sequence + 1, ack + 1)
        payload = b'\0' + b'\0\x0a' * 2 + b'\x20\x01\x0a'
        salt = table[sequence % 1020:sequence % 1020 + 4]
        crc = binascii.crc_hqx(payload + bytes([(sequence & 255) ^ salt[0], salt[1], ((sequence >> 8) & 255) ^ salt[2], salt[3]]), 0xffff) & 255
        s.send(struct.pack('<IIH', sequence, ack | (reliable << 31), 12346) + b'\x03' + bytes([crc]) + payload)
        data = receive()
        if b'changing' in data or b'reconnect' in data:
            advanced = True
            break
        time.sleep(0.05)
    assert advanced, 'server did not leave intermission through the map cycle'
send('drop')
s.close()
time.sleep(0.5)
print('Client joined and disconnected.')
