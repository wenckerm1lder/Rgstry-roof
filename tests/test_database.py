import logging
import pathlib
import shutil
import sqlite3
from copy import deepcopy
from datetime import datetime

import pytest

from cincanregistry import VersionInfo, ToolInfo, VersionType
from cincanregistry.checkers import UpstreamChecker
from cincanregistry.database import ToolDatabase
from .fake_instances import (
    FAKE_VERSION_INFO_NO_CHECKER,
    FAKE_VERSION_INFO_WITH_CHECKER,
    FAKE_TOOL_INFO,
    FAKE_TOOL_INFO2,
    FAKE_CHECKER_CONF
)


@pytest.fixture(scope='function')
def base_db(caplog, config):
    caplog.set_level(logging.DEBUG)
    # Make sample database for other tests
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


def test_configure(config, caplog):
    caplog.set_level(logging.DEBUG)
    test_db = ToolDatabase(config)
    logs = [l.message for l in caplog.records]
    assert "Creating new database file..." in logs
    assert config.tool_db.is_file()


def test_db_tool_data_insert(config, caplog):
    caplog.set_level(logging.DEBUG)
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


def test_insert_tool_list(config, caplog):
    caplog.set_level(logging.DEBUG)
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


def test_db_tool_data_insert_with_versions(config, caplog):
    caplog.set_level(logging.DEBUG)
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
        # Still two versions
        assert len(n_tools[0].versions) == 2


def test_db_insert_duplicate_version(caplog, config):
    caplog.set_level(logging.DEBUG)
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
    versions = base_db.get_versions_by_tool(FAKE_TOOL_INFO.get("name"), [VersionType.REMOTE])
    assert len(versions) == 1
    assert versions[0].version == "0.9"
    assert versions[0].version_type == VersionType.REMOTE


def test_get_tool_by_remote(base_db, caplog):
    caplog.set_level(logging.DEBUG)
    tmp_tool = {
        "name": "test_tool_temp",
        "updated": datetime(2021, 3, 13, 13, 37),
        "location": "test_location",
        "description": "test_description",
    }
    with base_db.transaction():
        base_db.insert_tool_info(ToolInfo(**tmp_tool))
    tool = base_db.get_single_tool(tool_name=FAKE_TOOL_INFO.get("name"), remote_name=FAKE_TOOL_INFO.get("location"))
    assert tool.name == FAKE_TOOL_INFO.get("name")
    tool = base_db.get_single_tool(tool_name=FAKE_TOOL_INFO.get("name"), remote_name=FAKE_TOOL_INFO.get("location"),
                                   filter_by=[VersionType.UPSTREAM])
    assert len(tool.versions) == 1
    assert tool.versions[0].version_type == VersionType.UPSTREAM
    tool = base_db.get_single_tool(tool_name=FAKE_TOOL_INFO.get("name"), remote_name=FAKE_TOOL_INFO.get("location"),
                                   filter_by=[VersionType.REMOTE])
    assert len(tool.versions) == 1
    assert tool.versions[0].version_type == VersionType.REMOTE
    tmp_version = deepcopy(FAKE_VERSION_INFO_NO_CHECKER)
    tmp_version["version_type"] = VersionType.LOCAL
    with base_db.transaction():
        base_db.insert_version_info(tool, tmp_version)
    tool = base_db.get_single_tool(tool_name=FAKE_TOOL_INFO.get("name"), remote_name=FAKE_TOOL_INFO.get("location"),
                                   filter_by=[VersionType.REMOTE, VersionType.UPSTREAM])
    assert len(tool.versions) == 2
    assert VersionType.LOCAL not in [i.version_type for i in tool.versions]

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
        versions = base_db.get_versions_by_tool(FAKE_TOOL_INFO.get("name"), provider=tmp_checker.get("source"),
                                                latest=False)
        assert len(versions) == 2
        # Replace existing record with identical data but different date
        tmp_checker["updated"] = datetime(2018, 3, 3, 13, 37, )
        base_db.insert_version_info(ToolInfo(**FAKE_TOOL_INFO), VersionInfo(**tmp_checker))
        version = base_db.get_versions_by_tool(FAKE_TOOL_INFO.get("name"), provider=tmp_checker.get("source"),
                                               latest=True)
        assert version.version == "0.9"


def test_insert_meta_data(caplog, config):
    """Insert metadata of checker"""
    caplog.set_level(logging.DEBUG)
    test_db = ToolDatabase(config)
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    assert isinstance(ver2.source, UpstreamChecker)

    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)
    tool_obj.versions.append(ver2)
    with test_db.transaction():
        test_db.insert_tool_info(tool_obj)
        test_db.insert_meta_info(tool_obj.name, tool_obj.location, FAKE_CHECKER_CONF)
        meta_data = test_db.get_meta_information(tool_obj.name, FAKE_CHECKER_CONF.get("provider"))[0]
        assert meta_data.get("uri") == FAKE_CHECKER_CONF.get("uri")
        assert meta_data.get("repository") == FAKE_CHECKER_CONF.get("repository")
        assert meta_data.get("tool") == FAKE_CHECKER_CONF.get("tool")
        assert meta_data.get("provider") == FAKE_CHECKER_CONF.get("provider")
        assert meta_data.get("method") == FAKE_CHECKER_CONF.get("method")
        assert meta_data.get("suite") == FAKE_CHECKER_CONF.get("suite")
        assert meta_data.get("origin") == FAKE_CHECKER_CONF.get("origin")
        assert meta_data.get("docker_origin") == FAKE_CHECKER_CONF.get("docker_origin")


def test_failed_constraints_meta_data(caplog, base_db):
    caplog.set_level(logging.DEBUG)
    # Null tool data
    tmp_conf = deepcopy(FAKE_CHECKER_CONF)
    tmp_conf["tool"] = None
    tmp_checker = {
        "version": "1.9",
        "version_type": VersionType.REMOTE,
        "source": "no_checker_case",
        "tags": {"latest", "latest-stable"},
        "updated": datetime(2021, 3, 3, 13, 37, ),
        "size": 89529754,
    }
    with pytest.raises(sqlite3.IntegrityError):
        with base_db.transaction():
            base_db.insert_version_info(ToolInfo(**FAKE_TOOL_INFO), VersionInfo(**tmp_checker))
            base_db.insert_meta_info(FAKE_TOOL_INFO.get("name"), FAKE_TOOL_INFO.get("location"), tmp_conf)
        # Rollback should happen, inserted version not found
        version = base_db.get_versions_by_tool(FAKE_TOOL_INFO.get("name"), provider=tmp_checker.get("source"),
                                               latest=True)
        assert version.version != "1.9"
        tools = base_db.get_tools()
        assert len(tools[0].versions) == 2


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
