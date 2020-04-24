# from unittest.mock import Mock
# from ..cinverman.toolinfo import VersionInfo
# from ..cinverman.checkers import *

# def get_fake_VersionInfo():

#     ret = VersionInfo(1.1, set(["latest", "latest-stable"]))
#     return

# def get_fake_GithubChecker():

#     checker = GitHubChecker()

#     return
from datetime import datetime
from unittest import mock
from cinverman.checkers import UpstreamChecker

FAKE_VERSION_INFO_NO_CHECKER = {
    "version": 0.9,
    "source": "no_checker_case",
    "tags": set(["latest", "latest-stable"]),
    "updated": datetime(2020, 3, 3, 13, 37,),
}

FAKE_UPSTREAM_CHECKER = mock.Mock(spec=UpstreamChecker)
FAKE_UPSTREAM_CHECKER.uri = "https://test.uri"
FAKE_UPSTREAM_CHECKER.repository = "test_repository"
FAKE_UPSTREAM_CHECKER.tool = "test_tool"
FAKE_UPSTREAM_CHECKER.provider = "test_provider"
FAKE_UPSTREAM_CHECKER.method = "test_release"
FAKE_UPSTREAM_CHECKER.suite = "test_suite"
FAKE_UPSTREAM_CHECKER.origin = True
FAKE_UPSTREAM_CHECKER.docker_origin = True
FAKE_UPSTREAM_CHECKER.version = "1.1"
FAKE_UPSTREAM_CHECKER.extra_info = "Test information"
FAKE_UPSTREAM_CHECKER.timeout = 30
# This value is used, if old value is stored more than 1 hour ago
FAKE_UPSTREAM_CHECKER.get_version.return_value = "1.2"
FAKE_UPSTREAM_CHECKER.__iter__ = UpstreamChecker.__iter__

FAKE_VERSION_INFO_WITH_CHECKER = {
    "version": 0.9,
    "source": FAKE_UPSTREAM_CHECKER,
    "tags": set(["latest", "latest-stable"]),
    "updated": datetime(2020, 3, 3, 13, 37,),
}


FAKE_TOOL_INFO = {
    "name": "test_tool",
    "updated": datetime(2020, 3, 13, 13, 37),
    "location": "test_location",
    "description": "test_description",
}
FAKE_TOOL_INFO2 = {
    "name": "test_tool_two",
    "updated": datetime(2020, 2, 12, 12, 27),
    "location": "test_location_two",
    "description": "test_description_two",
}


FAKE_CHECKER_CONF = {
    "uri": "https://test.uri",
    "repository": "test_repository",
    "tool": "test_tool",
    "provider": "test_provider",
    "method": "test_method",
    "suite": "test_suite",
    "origin": True,
    "docker_origin": True,
    "version": "test_version",
    "extra_info": "test_extra_info",
}

FAKE_CHECKER_TOKEN = "abcd1234efgh5678"
