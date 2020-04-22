from cinverman import VersionInfo, ToolInfo
from cinverman.checkers import UpstreamChecker
from datetime import datetime
from unittest import mock
import pytest
import json

from .fake_instances import (
    FAKE_VERSION_INFO_NO_CHECKER,
    FAKE_VERSION_INFO_WITH_CHECKER,
    FAKE_TOOL_INFO,
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
