from cincanregistry import VersionInfo, VersionType
from cincanregistry.checkers import UpstreamChecker
from datetime import datetime
from unittest import mock
import pytest
import json
from cincanregistry.utils import format_time
from .fake_instances import (
    FAKE_VERSION_INFO_NO_CHECKER,
    FAKE_VERSION_INFO_WITH_CHECKER,
)


@mock.patch.object(
    VersionInfo.__init__, "__defaults__", VersionInfo.__init__.__defaults__
)
def test_version_type_obj():
    """Testing enum of version types"""
    assert VersionType.LOCAL.value == "local"
    assert VersionType.REMOTE.value == "remote"
    assert VersionType.UPSTREAM.value == "upstream"
    assert VersionType.UNDEFINED.value == "undefined"

    assert isinstance(VersionType.LOCAL, VersionType)
    assert isinstance(VersionType.REMOTE, VersionType)
    assert isinstance(VersionType.UPSTREAM, VersionType)
    assert isinstance(VersionType.UNDEFINED, VersionType)


def test_create_version_info_no_checker():
    """
    Test init method and attribute content
    """
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj._version == "0.9"
    assert obj._source == "no_checker_case"
    assert obj._tags == {"latest", "latest-stable"}
    assert obj._updated == datetime(2020, 3, 3, 13, 37)
    assert obj._origin is False
    fake_d = FAKE_VERSION_INFO_NO_CHECKER.copy()
    fake_d["updated"] = "invalid_dateformat"
    with pytest.raises(ValueError):
        VersionInfo(**fake_d)
    fake_d["updated"] = FAKE_VERSION_INFO_NO_CHECKER.get("updated")
    with pytest.raises(ValueError):
        v_obj = VersionInfo(**fake_d)
        v_obj.version_type = ""


def test_getters_version_info_no_checker():
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)

    assert obj.version == "0.9"
    assert obj.provider == "no_checker_case"
    assert not obj.docker_origin
    assert obj.extra_info == ""
    assert obj.source == "no_checker_case"
    assert not obj.origin
    assert obj.tags == set(["latest", "latest-stable"])
    assert obj.updated == datetime(2020, 3, 3, 13, 37)
    assert obj.size == "39.53 MB"
    assert obj.raw_size() == 39529754


def test_setters_version_info_no_checker():
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj.source == "no_checker_case"
    obj.source = "new case"
    assert obj.source == "new case"
    assert obj.version == "0.9"
    obj.version = 1.2
    assert obj.version == "1.2"
    with pytest.raises(ValueError):
        obj.version = ""

    obj.updated = datetime(2020, 1, 1, 11, 11)
    obj.updated == datetime(2020, 1, 1, 11, 11)
    # Test invalid time format
    with pytest.raises(ValueError):
        obj.updated = ""

    # size
    with pytest.raises(ValueError):
        obj.size = "16062006"

    obj._size = None
    assert obj.size == "NaN"
    obj.size = 900
    assert obj.size == "900 bytes"
    obj.size = 1001
    assert obj.size == "1.00 KB"
    obj.size = 16062
    assert obj.size == "16.06 KB"
    obj.size = 16062006
    assert obj.size == "16.06 MB"
    obj.size = 1606200600
    assert obj.size == "1.61 GB"

    obj_c = FAKE_VERSION_INFO_NO_CHECKER.copy()
    obj_c["size"] = "This is something"
    obj = VersionInfo(**obj_c)
    assert obj.size == "NaN"


@mock.patch.object(
    VersionInfo.__init__, "__defaults__", VersionInfo.__init__.__defaults__
)
def test_create_version_info_with_checker():
    """
    Test init and attribute content
    """
    obj = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    obj._source.reset_mock()
    assert isinstance(obj._source, UpstreamChecker)
    assert obj.provider == "test_provider"
    assert obj.docker_origin
    assert obj.extra_info == "Test information"
    assert obj.version == "1.1"


def test_version_info_normalization():
    obj1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj1.get_normalized_ver() == [0, 9]
    obj1.version = "1.2.3.4.5.6"
    assert obj1.get_normalized_ver() == [1, 2, 3, 4, 5, 6]
    obj1.version = "1_2_3_4"
    assert obj1.get_normalized_ver() == [1, 2, 3, 4]
    obj1.version = "ghidra_9.1.2_PUBLIC_20200212"
    assert obj1.get_normalized_ver() == [9, 1, 2]
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

    obj1.version = "ABCDEFG"
    assert obj1.get_normalized_ver() == "ABCDEFG"


def test_version_info_str():
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert str(obj) == "0.9"


def test_version_info_eq():
    obj1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    obj2 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj1 == obj2
    obj1.version = 1.2
    assert obj1 != obj2
    # We can compare for strings.
    assert obj1 == "1.2"
    assert obj1 != "1.3"
    # But not integers
    with pytest.raises(ValueError):
        assert obj1 != 1


def test_version_info_format():
    obj1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert f"{obj1}" == "0.9"


def test_version_info_iter():
    obj = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    obj.updated = datetime.now()
    test_dict = {
        "version": "1.1",
        "version_type": "upstream",
        "source": {
            "uri": "https://test.uri",
            "repository": "test_repository",
            "tool": "test_tool",
            "provider": "test_provider",
            "method": "test_release",
            "suite": "test_suite",
            "origin": True,
            "docker_origin": True,
            "version": "1.1",
            "extra_info": "Test information",
        },
        "tags": ["latest", "latest-stable"],
        "updated": format_time(obj.updated),
        "origin": True,
        "size": "3.95 MB",
    }
    assert dict(obj) == test_dict
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    obj.updated = datetime.now()
    test_dict2 = {
        "version": "0.9",
        "version_type": "remote",
        "source": "no_checker_case",
        "tags": ["latest", "latest-stable"],
        "updated": format_time(obj.updated),
        "origin": False,
        "size": "39.53 MB",
    }
    assert dict(obj) == test_dict2

    assert json.dumps(test_dict)
    assert json.dumps(test_dict2)


def test_version_info_from_dict():
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    obj_dict = dict(obj)
    obj = VersionInfo.from_dict(obj_dict)
    assert obj.version == "0.9"
    assert obj.source == "no_checker_case"
    assert obj.tags == set(["latest-stable", "latest"])
    assert obj.updated == datetime(2020, 3, 3, 13, 37)
    assert obj.size == "39.53 MB"

    with pytest.raises(TypeError):
        VersionInfo.from_dict("not_dict")
