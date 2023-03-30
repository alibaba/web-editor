#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Thu Mar 30 2023 17:03:48 by codeskyblue
"""

import pathlib
import re
import pytest
from weditor.web import utils

@pytest.fixture
def hello_path(tmp_path: pathlib.Path) -> pathlib.Path:
    test_path = tmp_path / 'test.txt'
    test_path.write_text('hello')
    return test_path


def test_tostr():
    assert utils.tostr('hello') == "hello"


def test_read_file_content(hello_path: pathlib.Path):
    assert utils.read_file_content(hello_path) == b"hello"


def test_sha_file(hello_path: pathlib.Path):
    assert utils.sha_file(hello_path) == "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"


def test_write_file_content(hello_path: pathlib.Path):
    utils.write_file_content(hello_path, 'world')
    assert hello_path.read_text() == "world"


def test_current_ip():
    ip = utils.current_ip()
    assert re.match(r"\d+\.\d+\.\d+\.\d+", ip)