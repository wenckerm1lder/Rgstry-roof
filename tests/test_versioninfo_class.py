from cinverman.toolinfo import VersionInfo
from cinverman.checkers import UpstreamChecker
from datetime import datetime
from unittest import mock
import pytest
import json

from .fake_instances import (
    FAKE_VERSION_INFO_NO_CHECKER,
    FAKE_VERSION_INFO_WITH_CHECKER,
)


@mock.patch.object(
    VersionInfo.__init__, "__defaults__", VersionInfo.__init__.__defaults__
)
def test_create_version_info_no_checker():
    """
    Test init method and attribute content
    """
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj._version == "1.1"
    assert obj._source == "no_checker_case"
    assert obj._tags == set(["latest", "latest-stable"])
    assert obj._updated == datetime(2020, 3, 3, 13, 37)
    assert obj._origin is False


def test_getters_version_info_no_checker():

    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)

    assert obj.version == "1.1"
    assert obj.provider == "no_checker_case"
    assert not obj.docker_origin
    assert obj.extraInfo == ""
    assert obj.source == "no_checker_case"
    assert not obj.origin
    assert obj.tags == set(["latest", "latest-stable"])
    assert obj.updated == datetime(2020, 3, 3, 13, 37)


def test_setters_version_info_no_checker():

    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj.source == "no_checker_case"
    obj.source = "new case"
    assert obj.source == "new case"
    assert obj.version == "1.1"
    obj.version = 1.2
    assert obj.version == "1.2"
    with pytest.raises(ValueError):
        obj.version = ""

    obj.updated = datetime(2020, 1, 1, 11, 11)
    obj.updated == datetime(2020, 1, 1, 11, 11)
    # Test invalid time format
    with pytest.raises(ValueError):
        obj.updated = ""


@mock.patch.object(
    VersionInfo.__init__, "__defaults__", VersionInfo.__init__.__defaults__
)
def test_create_version_info_with_checker():
    """
    Test init and attribute content
    """
    obj = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    assert isinstance(obj._source, UpstreamChecker)
    assert obj.provider == "test_provider"
    assert obj.docker_origin
    assert obj.extraInfo == "Test information"
    # NOTE 1.1 version used in instansing gets ignored, if there is UpstreamChecker
    # Note that instanced version in UpstreamChecker is older (0.9) - get_version returns newer
    assert obj.version == "1.0"
    obj._source.get_version.assert_called_once()
    # New attempt with new time - using stored info from UpstreamChecker
    obj = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    obj.updated = datetime.now()
    assert obj.version == "0.9"


def test_version_info_normalization():
    obj1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj1.get_normalized_ver() == [1, 1]
    obj1.version = "1.2.3.4.5.6"
    assert obj1.get_normalized_ver() == [1, 2, 3, 4, 5, 6]
    obj1.version = "release-1.2.3"
    assert obj1.get_normalized_ver() == [1, 2, 3]
    # sha1 test - 40 char
    obj1.version = "ee9f16b4b95c28f8f79a39ca6a1840d8a6444c10"
    assert obj1.get_normalized_ver() == "ee9f16b4b95c28f8f79a39ca6a1840d8a6444c10"
    # sha256 test - 64 char
    obj1.version = "f8b09fba9fda9ffebae86611261cf628bd71022fb4348d876974f7c48ddcc6d5"
    assert (
        obj1.get_normalized_ver()
        == "f8b09fba9fda9ffebae86611261cf628bd71022fb4348d876974f7c48ddcc6d5"
    )
    # missing couple characters from sha256 length
    obj1.version = "f809fba9fda9ffebae86611261cf628bd71022fb4348d876974f7c48ddcc65"
    assert obj1.get_normalized_ver() == [809998661126162871022434887697474865]


def test_version_info_str():

    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert str(obj) == "1.1"


def test_version_info_eq():

    obj1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    obj2 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj1 == obj2
    obj1.version = 1.2
    assert obj1 != obj2
    with pytest.raises(ValueError):
        assert obj1 != 1


def test_version_info_format():
    obj1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert f"{obj1}" == "1.1"


def test_version_info_iter():
    obj = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    obj.updated = datetime.now()
    test_dict = {
        "version": "0.9",
        "source": {
            "uri": "https://test.uri",
            "repository": "test_repository",
            "tool": "test_tool",
            "provider": "test_provider",
            "method": "test_release",
            "suite": "test_suite",
            "origin": True,
            "docker_origin": True,
            "version": "0.9",
            "extra_info": "Test information",
        },
        "tags": ["latest", "latest-stable"],
        "updated": str(obj.updated),
        "origin": True,
    }
    assert dict(obj) == test_dict
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    obj.updated = datetime.now()
    test_dict2 = {
        "version": "1.1",
        "source": "no_checker_case",
        "tags": ["latest", "latest-stable"],
        "updated": str(obj.updated),
        "origin": False,
    }
    assert dict(obj) == test_dict2

    assert json.dumps(test_dict)
    assert json.dumps(test_dict2)
