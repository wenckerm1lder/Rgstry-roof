from cinverman.checkers import UpstreamChecker
from ..fake_instances import FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN
import pytest


class InvalidChecker(UpstreamChecker):
    def __init__(self):
        super().__init__()


class FakeChecker(UpstreamChecker):
    def __init__(self, tool_info, token="", timeout=20):
        super().__init__(tool_info, token=token, timeout=timeout)

    def _get_version(self, curr_ver=""):
        self.extra_info = "The Latest One"
        self.version = "latest"


def test_upstream_checker_create_invalid_childclass():
    """Test invalid child class implementation """
    with pytest.raises(TypeError):
        InvalidChecker()


def test_upstream_checker_create():
    """
    Test implementation of abstract 'UpstreamChecker' with fake child class
    and values.
    """
    checker = FakeChecker(FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN)

    assert checker.uri == "https://test.uri"
    assert checker.repository == "test_repository"
    assert checker.tool == "test_tool"
    assert checker.provider == "test_provider"
    assert checker.method == "test_method"
    assert checker.suite == "test_suite"
    assert checker.origin == "test_origin"
    assert checker.docker_origin == "test_docker_origin"
    # Unable to init following two attributes
    assert checker.version == ""
    assert checker.extra_info == ""
    # token
    assert checker.token == FAKE_CHECKER_TOKEN


def test_upstream_checker_get_version():
    checker = FakeChecker(FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN)
    assert checker.get_version() == "latest"
    assert checker.extra_info == "The Latest One"


def test_upstream_checker_iter():
    checker = FakeChecker(FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN)
    checker.get_version()
    dict(checker) == {
        "uri": "https://test.uri",
        "repository": "test_repository",
        "tool": "test_tool",
        "provider": "test_provider",
        "method": "test_method",
        "suite": "test_suite",
        "origin": "test_origin",
        "docker_origin": "test_docker_origin",
        "version": "latest",
        "extra_info": "The Latest One",
    }
