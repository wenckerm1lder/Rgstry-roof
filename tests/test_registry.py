from cincanregistry.registry import ToolRegistry
from cincanregistry.utils import parse_file_time
import pathlib
import docker
import logging
import requests
import pytest
from unittest import mock
from .fake_instances import FAKE_IMAGE_ATTRS, FAKE_DOCKER_REGISTRY_ERROR, FAKE_MANIFEST

TEST_REPOSITORY = "cincan/test"
TEST_EXTERNAL_API = True


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


def test_docker_registry_api_error(mocker, caplog):
    reg = ToolRegistry()
    caplog.set_level(logging.DEBUG)
    response = mock.Mock(ok=True)
    response.json.return_value = FAKE_DOCKER_REGISTRY_ERROR

    reg._docker_registry_API_error(response)

    logs = [l.message for l in caplog.records]
    assert logs == [f"400: Big error... Additional details: This is why!"]
    caplog.clear()
    caplog.set_level(logging.ERROR)
    reg._docker_registry_API_error(response, "Big cathastrope")
    logs = [l.message for l in caplog.records]
    assert logs == ["Big cathastrope"]


@pytest.mark.external_api
def test_get_service_token(mocker):
    reg = ToolRegistry()
    with requests.Session() as s:
        assert reg._get_registry_service_token(s, "cincan/test")
        ret = mock.Mock(ok=True)
        ret.status_code = 404
        ret.json.return_value = FAKE_DOCKER_REGISTRY_ERROR
        mocker.patch.object(s, "get", return_value=ret, autospec=True)
        assert not reg._get_registry_service_token(s, "cincan/test")


def test_get_version_by_image_id(mocker):
    mock_image = mock.Mock(spec=docker.models.images.Image)
    mock_image.attrs = FAKE_IMAGE_ATTRS
    reg = ToolRegistry()
    reg.client = mock.Mock()
    mocker.patch.object(
        reg.client, "ping", return_value=True, autospec=True,
    )
    assert reg._is_docker_running()
    mocker.patch.object(
        reg.client.images,
        "get",
        return_value=mock_image,
        autospec=docker.models.images.Image,
        create=True,
        spec_set=True,
    )
    assert reg.get_version_by_image_id("test_id") == "0.2"


@pytest.mark.external_api
def test_fetch_manifest(mocker):
    reg = ToolRegistry()
    with requests.Session() as s:
        # Test against real API
        manifest = reg.fetch_manifest(s, "cincan/test", "latest")
        assert manifest.get("tag") == "latest"
        assert manifest.get("name") == "cincan/test"
        assert manifest.get("schemaVersion") == 1
        assert manifest.get("history")
        assert manifest.get("signatures")
        assert manifest.get("fsLayers")
        assert manifest.get("architecture")

        ret = mock.Mock(ok=True)
        ret.status_code = 404
        ret.json.return_value = FAKE_DOCKER_REGISTRY_ERROR
        mocker.patch.object(s, "get", return_value=ret, autospec=True)
        assert not reg.fetch_manifest(s, "cincan/test", "latest")


def test_get_version_from_manifest(mocker, caplog):
    reg = ToolRegistry()
    assert "1.0", parse_file_time(
        "2020-05-23T19:43:14.106177342Z"
    ) == reg._get_version_from_manifest(FAKE_MANIFEST)

    manifest_c = FAKE_MANIFEST.copy()
    manifest_c["history"][0] = {
        "v1Compatibility": '{"architecture":"amd64","config":{"Hostname":"","Domainname":"","User":"","AttachStdin":false,"AttachStdout":false,"AttachStderr":false,"Tty":false,"OpenStdin":false,"StdinOnce":false,"Env":["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","TOOL_VERSION"],"Cmd":["echo","Hello, '
        'world!"],"Image":"sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4","Volumes":null,"WorkingDir":"","Entrypoint":null,"OnBuild":null,"Labels":{"MAINTAINER":"cincan.io"}},"container":"6e470d761c29de22781774ab9ab5e16678f1a603ba2f5c0a6b83c8597bd63b7a","container_config":{"Hostname":"6e470d761c29","Domainname":"","User":"","AttachStdin":false,"AttachStdout":false,"AttachStderr":false,"Tty":false,"OpenStdin":false,"StdinOnce":false,"Env":["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","TOOL_VERSION=1.0"],"Cmd":["/bin/sh","-c","#(nop) '
        '","CMD [\\"echo\\" \\"Hello, '
        'world!\\"]"],"Image":"sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4","Volumes":null,"WorkingDir":"","Entrypoint":null,"OnBuild":null,"Labels":{"MAINTAINER":"cincan.io"}},"created":"2020-05-23T19:43:14.106177342Z","docker_version":"19.03.8-ce","id":"5dfc05a56cc5819bb4dec3f7d19f908566c4d115457a1be8cc02ca87cc8d81c0","os":"linux","parent":"7099d9ed2d5fca9f9a65e010826d70a5fd5c53d64a5590292a89e106f8f98d6d","throwaway":true}'
    }
    caplog.set_level(logging.WARNING)
    assert (
        "",
        parse_file_time("2020-05-23T19:43:14.106177342Z"),
    ) == reg._get_version_from_manifest(manifest_c)
    logs = [l.message for l in caplog.records]
    assert logs == [
        "No version information for tool cincan/test: list index out of range"
    ]
