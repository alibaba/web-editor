import pytest
from weditor.web.proto import PlatformEnum


def test_PlatformEnum():
    assert PlatformEnum.AndroidADB == "AndroidADB"