from cincanregistry import VersionInfo, VersionType, ToolInfo, ToolInfoEncoder
from cincanregistry.utils import format_time
from datetime import datetime
import pytest
import json
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
    tool_obj.versions.append(ver2)

    assert tool_obj.name == "test_tool"
    assert tool_obj.updated == datetime(2020, 3, 13, 13, 37)
    assert tool_obj.location == "test_location"
    assert tool_obj.description == "test_description"

    assert tool_obj.versions[0].version == "0.9"
    assert tool_obj.versions[1].version == "1.1"

    assert len(tool_obj.versions) == 2

    with pytest.raises(ValueError):
        ToolInfo("", datetime.now(), "test-location")

    with pytest.raises(ValueError):
        ToolInfo(1234, datetime.now(), "test-location")


def test_tool_info_set():
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)

    # Unable to change name
    with pytest.raises(AttributeError):
        tool_obj.name = "new_name"

    with pytest.raises(ValueError):
        tool_obj.updated = "16062006"

    tool_obj.updated = datetime(2020, 3, 11, 11, 37)
    assert tool_obj.updated == datetime(2020, 3, 11, 11, 37)


def test_tool_info_origin_version():
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)

    assert tool_obj.get_origin_version() == VersionInfo(
        "Not implemented", VersionType.UNDEFINED, "", set(), datetime.min
    )
    assert tool_obj.get_docker_origin_version() == VersionInfo(
        "Not implemented", VersionType.UNDEFINED, "", set(), datetime.min
    )

    tool_obj.versions.append(ver2)

    assert tool_obj.get_origin_version() == "1.1"
    # Above fetch updated timestamp when getting 1.2 version with 'get_version' method, because
    # timestamp was older than 1 hour
    # However, this is mock object, and does not update original object as real UpstreamCheck
    # Object would do - therefore we are getting version 1.1 in next fetch, because VersionInfo
    # has timestamp updated
    assert tool_obj.get_docker_origin_version() == "1.1"


def test_tool_info_latest_version():
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)
    tool_obj.versions.append(ver2)

    assert tool_obj.get_latest() == "0.9"
    assert tool_obj.get_latest(in_upstream=True) == "1.1"

    # No versions at all
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    assert tool_obj.get_latest() == VersionInfo("undefined", VersionType.UNDEFINED, "", set(), datetime.min)


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
    # Different version
    tool_obj.versions[0].version = "NOT_SAME"
    assert tool_obj != tool_obj2

    # Test different names
    tool_obj = ToolInfo(**FAKE_TOOL_INFO2)
    tool_obj.versions.append(ver1)
    assert tool_obj != tool_obj2

    # Invalid type comparison
    with pytest.raises(ValueError):
        assert tool_obj == "Heheehe"


def test_tool_info_iter():
    t_info = ToolInfo(**FAKE_TOOL_INFO)
    t_info.versions.append(VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER))
    t_info.versions.append(VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER))
    t_info_dict = dict(t_info)

    assert t_info_dict.get("name") == "test_tool"
    assert t_info_dict.get("updated") == "2020-03-13T13:37:00"
    assert t_info_dict.get("location") == "test_location"
    assert t_info_dict.get("description") == "test_description"
    assert t_info_dict.get("versions")[0] == {
        "version": "0.9",
        "version_type": VersionType.REMOTE.value,
        "source": "no_checker_case",
        "tags": ["latest", "latest-stable"],
        "updated": format_time(datetime(2020, 3, 3, 13, 37,)),
        "size": "39.53 MB",
        "origin": False,
    }


def test_tool_info_from_dict():
    t_info = ToolInfo(**FAKE_TOOL_INFO)
    t_info.versions.append(VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER))
    t_info.versions.append(VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER))
    t_info_dict = dict(t_info)
    t_info_from_dict = ToolInfo.from_dict(t_info_dict)
    assert t_info.name == t_info_from_dict.name
    assert t_info.updated == t_info_from_dict.updated
    assert t_info.location == t_info_from_dict.location
    assert t_info.versions[1].version == t_info_from_dict.versions[1].version
    assert t_info.versions[1].version == "1.1"

    with pytest.raises(TypeError):
        ToolInfo.from_dict("not_dict")

    assert json.dumps(t_info, cls=ToolInfoEncoder)