from cincanregistry import Remotes
from cincanregistry.toolregistry import ToolRegistry
from cincanregistry.configuration import Configuration
import pathlib
import logging
import requests


def test_create_registry(mocker, caplog):
    caplog.set_level(logging.DEBUG)
    # Ignore possible configuration file in local filesystem
    mocker.patch("builtins.open", side_effect=IOError())
    mocker.patch.object(pathlib.Path, "is_file", return_value=False)

    logging.getLogger("docker").setLevel(logging.WARNING)
    reg = ToolRegistry(default_remote=Remotes.DOCKERHUB)
    reg.remote_registry._set_auth_and_service_location()
    assert reg.logger
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
    assert logs[:1] == [
        f"No configuration file found for registry in location: {reg.config.file}"
    ]


def test_is_docker_running(mocker, caplog):
    caplog.set_level(logging.ERROR)
    reg = ToolRegistry()
    mocker.patch.object(
        reg.local_registry.client,
        "ping",
        return_value=False,
        side_effect=requests.exceptions.ConnectionError(),
    )
    assert not reg.local_registry._is_docker_running()
    logs = [l.message for l in caplog.records]
    assert logs == [
        "Failed to connect to Docker Server. Is it running?",
        "Not able to list or use local tools.",
    ]

    mocker.patch.object(
        reg.local_registry.client, "ping", return_value=True, autospec=True,
    )
    assert reg.local_registry._is_docker_running()
