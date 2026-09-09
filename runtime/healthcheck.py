#!/usr/bin/env python3
import os
import socket
import sys


def check():
    service = os.environ.get('QW_SERVICE', 'server')
    if service == 'qtv':
        port = int(os.environ.get('QTV_PORT', '28000'))
        with socket.create_connection(('127.0.0.1', port), timeout=2) as sock:
            sock.sendall(b'GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
            return sock.recv(1024).startswith(b'HTTP/1.')
    key, default = ('QWFWD_PORT', '30000') if service == 'qwfwd' else ('QW_PORT', '27500')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(2)
        sock.connect(('127.0.0.1', int(os.environ.get(key, default))))
        sock.send(b'\xff\xff\xff\xffstatus\n')
        result = sock.recv(8192)
        return result.startswith(b'\xff\xff\xff\xffn') and b'\\' in result[5:]


if __name__ == '__main__':
    try:
        sys.exit(0 if check() else 1)
    except (OSError, ValueError):
        sys.exit(1)
