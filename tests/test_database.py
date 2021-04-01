import pathlib
import shutil
import logging
from cincanregistry import VersionInfo, ToolInfo, ToolInfoEncoder
from cincanregistry.utils import format_time
from datetime import datetime
from cincanregistry.database import ToolDatabase
from cincanregistry.configuration import Configuration
import pytest
from .fake_instances import (
    FAKE_VERSION_INFO_NO_CHECKER,
    FAKE_VERSION_INFO_WITH_CHECKER,
    FAKE_TOOL_INFO,
    FAKE_TOOL_INFO2,
)


def test_configure(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    db_path = tmp_path / "test_db.sqlite"
    config = Configuration()
    config.tool_db = db_path
    test_db = ToolDatabase(config)
    logs = [l.message for l in caplog.records]
    assert "Creating new database file..." in logs
    assert db_path.is_file()


def test_db_tool_data_insert(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    db_path = tmp_path / "test_db.sqlite"
    config = Configuration()
    config.tool_db = db_path
    test_db = ToolDatabase(config)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    with test_db.transaction():
        test_db.insert_tool_info(tool_obj)
        # Duplicate insert, should be handled gracefully
        test_db.insert_tool_info(tool_obj)
    # Read data
    with test_db.transaction():
        tools = test_db.get_tools()
    assert len(tools) == 1
    assert tools[0].description == FAKE_TOOL_INFO.get("description")
    assert tools[0].name == FAKE_TOOL_INFO.get("name")
    assert tools[0].updated == FAKE_TOOL_INFO.get("updated")
    assert tools[0].location == FAKE_TOOL_INFO.get("location")


def test_insert_tool_list(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    db_path = tmp_path / "test_db.sqlite"
    config = Configuration()
    config.tool_db = db_path
    test_db = ToolDatabase(config)
    tools = [ToolInfo(**FAKE_TOOL_INFO), ToolInfo(**FAKE_TOOL_INFO2)]
    with test_db.transaction():
        test_db.insert_tool_info(tools)
    # Read values
    with test_db.transaction():
        tools_from_db = test_db.get_tools()
    assert len(tools_from_db) == 2
    assert tools[0].description == FAKE_TOOL_INFO.get("description")
    assert tools[0].name == FAKE_TOOL_INFO.get("name")
    assert tools[0].updated == FAKE_TOOL_INFO.get("updated")
    assert tools[0].location == FAKE_TOOL_INFO.get("location")
    assert tools[1].description == FAKE_TOOL_INFO2.get("description")
    assert tools[1].name == FAKE_TOOL_INFO2.get("name")
    assert tools[1].updated == FAKE_TOOL_INFO2.get("updated")
    assert tools[1].location == FAKE_TOOL_INFO2.get("location")


def test_db_tool_data_insert_with_versions(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    db_path = tmp_path / "test_db.sqlite"
    config = Configuration()
    config.tool_db = db_path
    test_db = ToolDatabase(config)
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)
    tool_obj.versions.append(ver2)
    with test_db.transaction():
        test_db.insert_tool_info(tool_obj)
        # Duplicate insert, should be handled gracefully
        test_db.insert_tool_info(tool_obj)
        n_tools = test_db.get_versions_by_tool(tool_obj.name)
        assert len(n_tools) == 1
        test_db.get_versions_by_tool()
        assert len(n_tools[0].versions) == 2

def test_invalid_types():
    # TODO add tests with invalid data type inserts, handle them gracefully on the code
    pass

@pytest.fixture(scope="session", autouse=True)
def delete_temporary_files(request, tmp_path_factory):
    """Cleanup a testing directory once we are finished."""
    _tmp_path_factory = tmp_path_factory

    def cleanup():
        tmp_path = _tmp_path_factory.getbasetemp()
        if pathlib.Path(tmp_path).exists() and pathlib.Path(tmp_path).is_dir():
            shutil.rmtree(tmp_path)

    request.addfinalizer(cleanup)
