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

    