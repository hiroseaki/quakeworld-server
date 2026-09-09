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
s.send(b'\xff'*4 + b'connect 28 12346 ' + challenge + b' "\\name\\lifecycle-test\\rate\\10000"\n')
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
send('drop')
s.close()
time.sleep(0.5)
print('Client joined and disconnected.')
