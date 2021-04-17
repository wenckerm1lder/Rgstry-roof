import pytest
import logging
import datetime
from unittest import mock
from cincanregistry import ToolInfo
from cincanregistry.remotes import DockerHubRegistry
from cincanregistry.models.manifest import ConfigReference, LayerObject
from cincanregistry.utils import parse_file_time
from .fake_instances import FAKE_DOCKER_REGISTRY_ERROR, FAKE_MANIFEST, TEST_REPOSITORY


def test_docker_registry_api_error(mocker, caplog, config):
    reg = DockerHubRegistry(configuration=config)
    caplog.set_level(logging.DEBUG)
    response = mock.Mock(ok=True)
    response.json.return_value = FAKE_DOCKER_REGISTRY_ERROR

    reg._docker_registry_api_error(response)

    logs = [l.message for l in caplog.records]
    assert logs == [f"400: Big error... Additional details: This is why!"]
    caplog.clear()
    caplog.set_level(logging.ERROR)
    reg._docker_registry_api_error(response, "Big catastrophe")
    logs = [l.message for l in caplog.records]
    assert logs == ["Big catastrophe"]


@pytest.mark.external_api
def test_get_service_token(mocker, config):
    reg = DockerHubRegistry(configuration=config)
    assert reg._get_registry_service_token(TEST_REPOSITORY)
    ret = mock.Mock(ok=True)
    ret.status_code = 404
    ret.json.return_value = FAKE_DOCKER_REGISTRY_ERROR
    mocker.patch.object(reg.session, "get", return_value=ret, autospec=True)
    assert not reg._get_registry_service_token(TEST_REPOSITORY)


@pytest.mark.external_api
def test_fetch_manifest(mocker, config):
    reg = DockerHubRegistry(configuration=config)
    # Test against real API
    manifest = reg.fetch_manifest(TEST_REPOSITORY, "dev")
    assert manifest.schemaVersion == 2
    assert manifest.mediaType == "application/vnd.docker.distribution.manifest.v2+json"
    assert isinstance(manifest.config, ConfigReference)
    assert isinstance(manifest.layers[0], LayerObject)
    ret = mock.Mock(ok=True)
    ret.status_code = 404
    ret.json.return_value = FAKE_DOCKER_REGISTRY_ERROR
    mocker.patch.object(reg.session, "get", return_value=ret, autospec=True)
    assert not reg.fetch_manifest(TEST_REPOSITORY, "dev")


@pytest.mark.external_api
def test_get_version_from_manifest(mocker, caplog, config):
    """Test for deprecated v1 manifest"""
    reg = DockerHubRegistry(configuration=config)
    assert "1.0", parse_file_time(
        "2020-05-23T19:43:14.106177342Z"
    ) == reg._get_version_from_manifest(FAKE_MANIFEST)

    manifest_c = FAKE_MANIFEST.copy()
    manifest_c["history"][0] = {
        "v1Compatibility": '{"architecture":"amd64","config":{"Hostname":"","Domainname":"","User":"",'
                           '"AttachStdin":false,"AttachStdout":false,"AttachStderr":false,"Tty":false,'
                           '"OpenStdin":false,"StdinOnce":false,"Env":['
                           '"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","TOOL_VERSION"],'
                           '"Cmd":["echo","Hello, '
                           'world!"],"Image":"sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4'
                           '","Volumes":null,"WorkingDir":"","Entrypoint":null,"OnBuild":null,"Labels":{'
                           '"MAINTAINER":"cincan.io"}},'
                           '"container":"6e470d761c29de22781774ab9ab5e16678f1a603ba2f5c0a6b83c8597bd63b7a",'
                           '"container_config":{"Hostname":"6e470d761c29","Domainname":"","User":"",'
                           '"AttachStdin":false,"AttachStdout":false,"AttachStderr":false,"Tty":false,'
                           '"OpenStdin":false,"StdinOnce":false,"Env":['
                           '"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","TOOL_VERSION=1.0"],'
                           '"Cmd":["/bin/sh","-c","#(nop) ","CMD [\\"echo\\" \\"Hello, world!\\"]"],'
                           '"Image":"sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4",'
                           '"Volumes":null,"WorkingDir":"","Entrypoint":null,"OnBuild":null,"Labels":{'
                           '"MAINTAINER":"cincan.io"}},"created":"2020-05-23T19:43:14.106177342Z",'
                           '"docker_version":"19.03.8-ce",'
                           '"id":"5dfc05a56cc5819bb4dec3f7d19f908566c4d115457a1be8cc02ca87cc8d81c0","os":"linux",'
                           '"parent":"7099d9ed2d5fca9f9a65e010826d70a5fd5c53d64a5590292a89e106f8f98d6d",'
                           '"throwaway":true} '
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


@pytest.mark.external_api
def test_fetch_tags(mocker, caplog, config):
    reg = DockerHubRegistry(configuration=config)
    caplog.set_level(logging.INFO)
    tool_info = ToolInfo(TEST_REPOSITORY, datetime.datetime.now(), "remote")
    reg.fetch_tags(tool_info, update_cache=False)
    assert tool_info.name == TEST_REPOSITORY
    assert len(tool_info.versions) == 1
    assert tool_info.versions[0].version == "1.0"
    assert tool_info.versions[0].tags == {"dev"}

    logs = [l.message for l in caplog.records]
    assert logs == [
        "fetch cincan/test..."
    ]
    caplog.clear()
    caplog.set_level(logging.ERROR)
    ret = mock.Mock(ok=True)
    ret.status_code = 404
    ret.content = "Not Found"
    mocker.patch.object(reg.session, "get", return_value=ret, autospec=True)
    tool_info = ToolInfo(TEST_REPOSITORY, datetime.datetime.now(), "remote")
    reg.fetch_tags(tool_info, update_cache=False)
    logs = [l.message for l in caplog.records]
    assert logs == [
        "Error when getting tags for tool cincan/test: Not Found"
    ]
