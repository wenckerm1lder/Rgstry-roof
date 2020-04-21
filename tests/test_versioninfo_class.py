from cinverman.toolinfo import VersionInfo
from datetime import datetime
import pytest
from unittest import mock

FAKE_VERSION_INFO_NO_CHECKER = {
    "version": 1.1,
    "source": "no_checker_case",
    "tags": set(["latest", "latest-stable"]),
    "updated": datetime(2020, 3, 3, 13, 37,),
}


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

@mock.patch.object(
    VersionInfo.__init__, "__defaults__", VersionInfo.__init__.__defaults__
)
def test_create_version_info_with_checker():
    """
    Test init and attribute content
    """
    obj = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    # assert obj._version == "1.1"
    # assert obj._source == "no_checker_case"
    # assert obj._tags == set(["latest", "latest-stable"])
    # assert obj._updated == datetime(2020, 3, 3, 13, 37)
    # assert obj._origin is False


def test_version_info_normalization():
    obj1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    assert obj1.get_normalized_ver() == [1, 1]
    obj1.version = "1.2.3.4.5.6"
    assert obj1.get_normalized_ver() == [1, 2, 3, 4, 5, 6]
    obj1.version = "release-1.2.3"
    assert obj1.get_normalized_ver() == [1, 2, 3]
    # sha1 test
    obj1.version = "ee9f16b4b95c28f8f79a39ca6a1840d8a6444c10"
    assert obj1.get_normalized_ver() == "ee9f16b4b95c28f8f79a39ca6a1840d8a6444c10"
    # sha256 test
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
