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


def test_db_tool_data(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    db_path = tmp_path / "test_db.sqlite"
    config = Configuration()
    config.tool_db = db_path
    test_db = ToolDatabase(config)
    ver1 = VersionInfo(**FAKE_VERSION_INFO_NO_CHECKER)
    ver2 = VersionInfo(**FAKE_VERSION_INFO_WITH_CHECKER)
    tool_obj = ToolInfo(**FAKE_TOOL_INFO)
    tool_obj.versions.append(ver1)
    tool_obj.upstream_v.append(ver2)


@pytest.fixture(scope="session", autouse=True)
def delete_temporary_files(request, tmp_path_factory):
    """Cleanup a testing directory once we are finished."""
    _tmp_path_factory = tmp_path_factory

    def cleanup():
        tmp_path = _tmp_path_factory.getbasetemp()
        if pathlib.Path(tmp_path).exists() and pathlib.Path(tmp_path).is_dir():
            shutil.rmtree(tmp_path)

    request.addfinalizer(cleanup)
