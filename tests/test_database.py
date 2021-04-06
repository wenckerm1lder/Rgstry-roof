import logging
import pathlib
import shutil
from copy import deepcopy
from datetime import datetime

import pytest

from cincanregistry import VersionInfo, ToolInfo, VersionType
from cincanregistry.configuration import Configuration
from cincanregistry.database import ToolDatabase
from .fake_instances import (
    FAKE_VERSION_INFO_NO_CHECKER,
    FAKE_VERSION_INFO_WITH_CHECKER,
    FAKE_TOOL_INFO,
    FAKE_TOOL_INFO2,
)


@pytest.fixture(scope='function')
def base_db(caplog, tmp_path):
    caplog.set_level(logging.DEBUG)
    # Make sample database for other tests
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
        tool_obj2 = ToolInfo(**FAKE_TOOL_INFO2)
        tool_obj2.versions.append(ver1)
        tool_obj2.versions.append(ver2)
        test_db.insert_tool_info(tool_obj2)
    yield test_db


def test_base_db(caplog, base_db):
    tools = base_db.get_tools()
    assert len(tools) == 2
    assert len(tools[0].versions) == 2
    assert len(tools[1].versions) == 2

    assert tools[0].name == FAKE_TOOL_INFO.get("name")
    assert tools[1].name == FAKE_TOOL_INFO2.get("name")


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
        n_tools = test_db.get_tools()
        assert len(n_tools) == 1
        assert len(n_tools[0].versions) == 2
        n_versions = n_tools[0].versions
        assert n_versions[0].version == FAKE_VERSION_INFO_NO_CHECKER.get("version")
        assert n_versions[0].version_type == FAKE_VERSION_INFO_NO_CHECKER.get("version_type")
        assert n_versions[0].source == FAKE_VERSION_INFO_NO_CHECKER.get("source")
        assert n_versions[0].tags == FAKE_VERSION_INFO_NO_CHECKER.get("tags")
        # DB insert should not update time - should tell information of origin update time
        assert n_versions[0].updated == FAKE_VERSION_INFO_NO_CHECKER.get("updated")
        assert n_versions[0].raw_size() == FAKE_VERSION_INFO_NO_CHECKER.get("size")
        # Duplicate insert, should be handled gracefully
        test_db.insert_tool_info(tool_obj)
        n_tools = test_db.get_tools()
        # Should be three different versions, one updated when called
        assert len(n_tools[0].versions) == 3


def test_db_insert_duplicate_version(caplog, tmp_path):
    caplog.set_level(logging.DEBUG)
    db_path = tmp_path / "test_db.sqlite"
    config = Configuration()
    config.tool_db = db_path
    test_db = ToolDatabase(config)
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    cp_FAKE_VERSION_INFO_NO_CHECKER = deepcopy(FAKE_VERSION_INFO_NO_CHECKER)
    cp_FAKE_VERSION_INFO_NO_CHECKER["version"] = "1.1"
    ver3 = VersionInfo(**cp_FAKE_VERSION_INFO_NO_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)
    tool_obj.versions.append(ver2)
    tool_obj.versions.append(ver3)
    with test_db.transaction():
        test_db.insert_tool_info(tool_obj)
        tools_db = test_db.get_tools()
        assert len(tools_db[0].versions) == 2


def test_get_tool_by_name(tmp_path, caplog, base_db):
    """Tool by name, uses default db"""
    caplog.set_level(logging.DEBUG)
    tool = base_db.get_single_tool(FAKE_TOOL_INFO.get("name"))
    assert tool.name == FAKE_TOOL_INFO.get("name")
    tool = base_db.get_single_tool("non-existing")
    assert not tool


def test_get_tool_by_name_and_version_type(base_db, caplog):
    caplog.set_level(logging.DEBUG)
    versions = base_db.get_versions_by_tool(FAKE_TOOL_INFO.get("name"), VersionType.REMOTE)
    assert len(versions) == 1
    assert versions[0].version == "0.9"
    assert versions[0].version_type == VersionType.REMOTE


def test_get_tool_by_remote(base_db):
    tmp_tool = {
        "name": "test_tool_temp",
        "updated": datetime(2021, 3, 13, 13, 37),
        "location": "test_location",
        "description": "test_description",
    }
    base_db.insert_tool_info(ToolInfo(**tmp_tool))
    tool = base_db.get_single_tool(tool_name=FAKE_TOOL_INFO.get("name"), remote_name=FAKE_TOOL_INFO.get("location"))
    assert tool.name == FAKE_TOOL_INFO.get("name")

    tools = base_db.get_tools(remote_name=FAKE_TOOL_INFO.get("location"))
    assert len(tools) == 2


def test_get_latest_version_by_provider(base_db):
    tmp_checker = {
        "version": "1.9",
        "version_type": VersionType.REMOTE,
        "source": "no_checker_case",
        "tags": {"latest", "latest-stable"},
        "updated": datetime(2021, 3, 3, 13, 37, ),
        "size": 89529754,
    }
    with base_db.transaction():
        base_db.insert_version_info(ToolInfo(**FAKE_TOOL_INFO), VersionInfo(**tmp_checker))
        version = base_db.get_versions_by_tool(FAKE_TOOL_INFO.get("name"), provider=tmp_checker.get("source"),
                                               latest=True)
        assert version.version == "1.9"
        # Replace existing record with identical data but different date
        tmp_checker["updated"] = datetime(2018, 3, 3, 13, 37, )
        base_db.insert_version_info(ToolInfo(**FAKE_TOOL_INFO), VersionInfo(**tmp_checker))
        version = base_db.get_versions_by_tool(FAKE_TOOL_INFO.get("name"), provider=tmp_checker.get("source"),
                                               latest=True)
        assert version.version == "0.9"


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
