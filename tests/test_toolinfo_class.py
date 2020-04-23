from cinverman import VersionInfo, ToolInfo
from cinverman.checkers import UpstreamChecker
from datetime import datetime
import pytest

from .fake_instances import (
    FAKE_VERSION_INFO_NO_CHECKER,
    FAKE_VERSION_INFO_WITH_CHECKER,
    FAKE_TOOL_INFO,
    FAKE_TOOL_INFO2,
)


def test_create_tool_info():
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)
    tool_obj.upstream_v.append(ver2)

    assert tool_obj.name == "test_tool"
    assert tool_obj.updated == datetime(2020, 3, 13, 13, 37)
    assert tool_obj.location == "test_location"
    assert tool_obj.description == "test_description"

    assert next(iter(tool_obj.versions)).version == "0.9"
    assert next(iter(tool_obj.upstream_v)).version == "1.2"

    assert len(tool_obj.versions) == 1
    assert len(tool_obj.upstream_v) == 1

    with pytest.raises(ValueError):
        tool_obj2 = ToolInfo("", datetime.now(), "test-location")

    with pytest.raises(ValueError):
        tool_obj3 = ToolInfo(1234, datetime.now(), "test-location")


def test_tool_info_set():
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)

    # Unable to change name
    with pytest.raises(AttributeError):
        tool_obj.name = "new_name"

    with pytest.raises(ValueError):
        tool_obj.updated = "16062006"


def test_tool_info_origin_version():
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)

    assert tool_obj.getOriginVersion() == VersionInfo(
        "Not implemented", "", set(), datetime.min
    )
    assert tool_obj.getDockerOriginVersion() == VersionInfo(
        "Not implemented", "", set(), datetime.min
    )

    tool_obj.upstream_v.append(ver2)

    assert tool_obj.getOriginVersion() == "1.2"
    # Above fetch updated timestamp when getting 1.2 version with 'get_version' method, because
    # timestamp was older than 1 hour
    # However, this is mock object, and does not update original object as real UpstreamCheck
    # Object would do - therefore we are getting version 1.1 in next fetch, because VersionInfo
    # has timestamp updated
    assert tool_obj.getDockerOriginVersion() == "1.1"


def test_tool_info_latest_version():
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)
    tool_obj.upstream_v.append(ver2)

    assert tool_obj.getLatest() == "0.9"
    assert tool_obj.getLatest(in_upstream=True) == "1.1"
    assert ver2.source.get_version.called


def test_tool_info_to_str():
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    assert str(tool_obj) == "test_tool test_description"


def test_tool_info_eq():
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)
    tool_obj2 = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj2.versions.append(ver2)

    # Same name and version
    assert tool_obj == tool_obj2
    tool_obj.versions[0].version = "NOT_SAME"
    assert tool_obj != tool_obj2

    # Test different names
    tool_obj = ToolInfo(**FAKE_TOOL_INFO2)
    tool_obj.versions.append(ver1)
    assert tool_obj != tool_obj2
