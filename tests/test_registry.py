from cincanregistry.registry import ToolRegistry
import pathlib
from unittest import mock


def test_create_registry():

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


def test_get_version_by_image_id(mocker):
    reg = ToolRegistry()
    mocker.patch.object(reg, "_is_docker_running", return_value=True, autospec=True)
    print(reg._is_docker_running())

    # print(reg.get_version_by_image_id("a40b6ef99eab50c03f4c1bf6e28d95a5c88f0d001c343e871d7cb1c9fcecbb48"))


def test_update_tool_readme(mocker, tmpdir):
    p = tmpdir.mkdir("my_tool").join("README.md")
    p.write("# This is useful example tool.")
    reg = ToolRegistry()
    mocker.patch.object(reg, "_is_docker_running", return_value=True, autospec=True)
    print(reg._is_docker_running())
