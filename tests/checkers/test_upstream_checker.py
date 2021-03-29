from cincanregistry.checkers import UpstreamChecker
from ..fake_instances import FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN
import pytest
from unittest import mock
from requests.exceptions import Timeout, ConnectionError


class InvalidChecker(UpstreamChecker):
    def __init__(self):
        super().__init__()


class FakeChecker(UpstreamChecker):
    def __init__(self, tool_info, token="", timeout=20):
        super().__init__(tool_info, token=token, timeout=timeout)

    def _get_version(self, curr_ver=""):
        self.extra_info = "The Latest One"
        self.version = "latest"


def test_upstream_checker_create_invalid_child_class():
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
    assert checker.origin
    assert checker.docker_origin
    # Unable to init following two attributes
    assert checker.version == ""
    assert checker.extra_info == ""
    assert checker.logger
    assert checker.timeout == 20
    # token
    assert checker.token == FAKE_CHECKER_TOKEN

    # Test with missing or invalid values
    conf_cp = FAKE_CHECKER_CONF.copy()

    # Origin or docker_origin not boolean
    conf_cp["origin"] = "not_origin"
    with pytest.raises(ValueError):
        FakeChecker(conf_cp, FAKE_CHECKER_TOKEN)
    conf_cp["origin"] = True
    assert FakeChecker(conf_cp, FAKE_CHECKER_TOKEN)

    conf_cp["docker_origin"] = "not_origin"
    with pytest.raises(ValueError):
        FakeChecker(conf_cp, FAKE_CHECKER_TOKEN)
    conf_cp["docker_origin"] = True
    assert FakeChecker(conf_cp, FAKE_CHECKER_TOKEN)

    # uri or (tool and provider and repository) must be provided
    conf_cp["uri"] = ""
    conf_cp["provider"] = ""
    with pytest.raises(ValueError):
        FakeChecker(conf_cp, FAKE_CHECKER_TOKEN)

    conf_cp["uri"] = "http://valid.url"
    assert FakeChecker(conf_cp, FAKE_CHECKER_TOKEN)
    conf_cp["uri"] = ""
    conf_cp["provider"] = "some_provider"
    conf_cp["tool"] = ""
    with pytest.raises(ValueError):
        FakeChecker(conf_cp, FAKE_CHECKER_TOKEN)

    conf_cp["provider"] = "some_provider"
    conf_cp["tool"] = "some_tool"
    conf_cp["repository"] = ""
    with pytest.raises(ValueError):
        FakeChecker(conf_cp, FAKE_CHECKER_TOKEN)


def test_upstream_checker_get_version():
    """Test get_version method with some error cases"""
    checker = FakeChecker(FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN)
    assert checker.get_version() == "latest"
    assert checker.extra_info == "The Latest One"
    checker._get_version = mock.Mock(side_effect=Timeout)
    assert checker.get_version() == "Not found"
    checker.version = ""
    assert checker.version == ""
    checker._get_version = mock.Mock(side_effect=ConnectionError)
    assert checker.get_version() == "Not found"
    checker.version = ""
    resp = mock.Mock()
    resp.status_code = 403
    checker._get_version = mock.Mock(side_effect=checker._fail(resp))
    assert checker.get_version() == "Not found"


def test_upstream_checker_iter():
    checker = FakeChecker(FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN)
    checker.get_version()
    assert dict(checker) == {
        "uri": "https://test.uri",
        "repository": "test_repository",
        "tool": "test_tool",
        "provider": "test_provider",
        "method": "test_method",
        "suite": "test_suite",
        "origin": True,
        "docker_origin": True,
        "version": "latest",
        "extra_info": "The Latest One",
    }


def test_upstream_checker_tag_sort():
    """Test some tag sorting, impossible to make 100% valid"""
    tags = [
        {"ver": "1.2.3"},
        {"ver": "1.2.31"},
        {"ver": "2Of2f23-release"},
        {"ver": "1.2.32-release-third"},
        {"ver": "1w2e3r4t5yhfk3k65k3k1k3k5k64kk3k4k6k5"},
    ]
    checker = FakeChecker(FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN)
    assert (
            checker._sort_latest_tag(tags, tag_key="ver").get("ver")
            == "1.2.32-release-third"
    )


def test_string_format():
    checker = FakeChecker(FAKE_CHECKER_CONF, FAKE_CHECKER_TOKEN)
    assert FAKE_CHECKER_CONF.get("provider").lower() == str(checker)
