# coding: utf-8
#

import hashlib
import os
import socket

import six


def tostr(s, encoding='utf-8'):
    if six.PY2:
        return s.encode(encoding)
    if isinstance(s, bytes):
        return s.decode(encoding)
    return s


def read_file_content(filename, default=''):
    if not os.path.isfile(filename):
        return default
    with open(filename, 'rb') as f:
        return f.read()


def sha_file(path):
    sha = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha.update(data)
    return sha.hexdigest()


def write_file_content(filename, content):
    with open(filename, 'w') as f:
        f.write(content.encode('utf-8'))


def virt2real(path):
    return os.path.join(os.getcwd(), path.lstrip('/'))


def real2virt(path):
    return os.path.relpath(path, os.getcwd()).replace('\\', '/')


def current_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"
