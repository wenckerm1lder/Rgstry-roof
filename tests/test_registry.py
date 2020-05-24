from cincanregistry.registry import ToolRegistry
from cincanregistry.utils import parse_file_time
import pathlib
import docker
import logging
import requests
import pytest


def test_create_registry(mocker, caplog):
    caplog.set_level(logging.DEBUG)
    # Ignore possible configuration file in local filesystem
    mocker.patch("builtins.open", side_effect=IOError())

    logging.getLogger("docker").setLevel(logging.WARNING)
    reg = ToolRegistry()

    assert reg.logger
    assert reg.client
    assert reg.schema_version == "v2"
    assert reg.hub_url == "https://hub.docker.com/v2"
    assert reg.auth_url == "https://auth.docker.io/token"
    assert reg.registry_service == "registry.docker.io"
    assert reg.registry_host == "registry.hub.docker.com"
    assert reg.registry_url == "https://registry.hub.docker.com/v2"
    assert reg.max_workers == 30
    assert reg.max_page_size == 1000
    assert reg.version_var == "TOOL_VERSION"
    assert reg.conf_filepath == pathlib.Path.home() / ".cincan/registry.json"
    assert reg.tool_cache == pathlib.Path.home() / ".cincan" / "tools.json"
    assert reg.configuration == {}

    logs = [l.message for l in caplog.records]
    assert logs == [
        f"No configuration file found for registry in location: {reg.conf_filepath}"
    ]


def test_is_docker_running(mocker, caplog):
    caplog.set_level(logging.ERROR)
    reg = ToolRegistry()
    mocker.patch.object(
        reg.client,
        "ping",
        return_value=False,
        autospec=True,
        side_effect=requests.exceptions.ConnectionError(),
    )
    assert not reg._is_docker_running()
    logs = [l.message for l in caplog.records]
    assert logs == [
        "Failed to connect to Docker Server. Is it running?",
        "Not able to list or use local tools.",
    ]

    mocker.patch.object(
        reg.client, "ping", return_value=True, autospec=True,
    )
    assert reg._is_docker_running()
