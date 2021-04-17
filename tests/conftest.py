from cincanregistry.configuration import Configuration
import pathlib
import shutil

import pytest


@pytest.fixture(scope='function')
def config(tmp_path):
    """Generate configuration object, file in tmp path"""
    config_path = tmp_path / "registry.yaml"
    conf = Configuration(config_path=config_path)
    db_path = tmp_path / "test_db.sqlite"
    conf.tool_db = db_path
    yield conf


@pytest.fixture(scope="session", autouse=True)
def delete_temporary_files(request, tmp_path_factory):
    """Cleanup a testing directory once we are finished."""
    _tmp_path_factory = tmp_path_factory

    def cleanup():
        tmp_path = _tmp_path_factory.getbasetemp()
        if pathlib.Path(tmp_path).exists() and pathlib.Path(tmp_path).is_dir():
            shutil.rmtree(tmp_path)

    request.addfinalizer(cleanup)
