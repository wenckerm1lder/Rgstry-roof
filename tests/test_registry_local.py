import docker
import requests
from cincanregistry.daemon import DaemonRegistry
from cincanregistry.utils import parse_file_time
from unittest import mock
from .fake_instances import FAKE_IMAGE_ATTRS, TEST_REPOSITORY, FAKE_IMAGE, FAKE_IMAGE2, FAKE_IMAGE3


def test_get_version_by_image_id(mocker, config):
    mock_image = mock.Mock(spec=docker.models.images.Image)
    mock_image.attrs = FAKE_IMAGE_ATTRS
    reg = DaemonRegistry(configuration=config)
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
    assert reg.get_version_by_image_id("test_id") == "1.0"


def test_create_local_tool_info_by_name(mocker, config):
    reg = DaemonRegistry(configuration=config)
    reg.client = mock.Mock()
    mocker.patch.object(
        reg.client, "ping", return_value=False, side_effect=requests.exceptions.ConnectionError(),
    )
    assert not reg.create_local_tool_info_by_name(TEST_REPOSITORY)
    mocker.patch.object(
        reg.client, "ping", return_value=True,
    )
    mocker.patch.object(reg.client.images, "list", return_value=[FAKE_IMAGE, FAKE_IMAGE2, FAKE_IMAGE3], create=True)
    tool_info = reg.create_local_tool_info_by_name(TEST_REPOSITORY)
    assert tool_info.name == TEST_REPOSITORY
    assert len(tool_info.versions) == 2
    assert tool_info.versions[0].version == "1.0"
    assert tool_info.versions[0].tags == {"cincan/test:latest"}
    assert tool_info.versions[0].size == "5.59 MB"
    assert tool_info.versions[0].updated == parse_file_time("2020-05-23T19:43:14.106177342Z")
    mocker.patch.object(reg.client.images, "list", return_value=[], create=True)
    assert not reg.create_local_tool_info_by_name(TEST_REPOSITORY)
