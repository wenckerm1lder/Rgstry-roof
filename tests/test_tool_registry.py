import logging
import pathlib
from unittest import mock
import requests

from cincanregistry import Remotes
from cincanregistry.configuration import Configuration
from cincanregistry.toolregistry import ToolRegistry


def test_create_registry(mocker, caplog, config):
    caplog.set_level(logging.DEBUG)
    # Ignore possible configuration file in local filesystem
    mocker.patch("builtins.open", side_effect=IOError())
    mocker.patch.object(pathlib.Path, "is_file", return_value=False)

    logging.getLogger("docker").setLevel(logging.WARNING)
    reg = ToolRegistry(default_remote=Remotes.DOCKERHUB, configuration=config)
    reg.remote_registry._set_auth_and_service_location()
    assert reg.logger
    if reg.local_registry._is_docker_running():
        assert reg.local_registry.client
    assert reg.remote_registry.schema_version == "v2"
    assert reg.remote_registry.registry_root == "https://registry.hub.docker.com"
    assert reg.remote_registry.auth_url == "https://auth.docker.io/token"
    assert reg.remote_registry.registry_service == "registry.docker.io"
    assert reg.remote_registry.max_workers == 30
    assert reg.remote_registry.max_page_size == 1000
    assert reg.version_var == "TOOL_VERSION"
    assert reg.tool_cache == pathlib.Path.home() / ".cincan" / "cache" / "tools.json"
    assert isinstance(reg.config, Configuration)

    logs = [l.message for l in caplog.records]


def test_is_docker_running(mocker, caplog, config):
    caplog.set_level(logging.ERROR)
    reg = ToolRegistry(configuration=config)
    if not reg.local_registry.client:
        reg.local_registry.client = mock.Mock()
    mocker.patch.object(
        reg.local_registry.client,
        "ping",
        return_value=False,
        side_effect=requests.exceptions.ConnectionError(),
    )
    assert not reg.local_registry._is_docker_running()
    logs = [l.message for l in caplog.records]
    assert logs[-2:] == [
        "Failed to connect to Docker Server. Is it running?",
        "Not able to list or use local tools.",
    ]

    mocker.patch.object(
        reg.local_registry.client, "ping", return_value=True, autospec=True,
    )
    assert reg.local_registry._is_docker_running()
