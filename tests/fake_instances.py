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
    "version": 1.1,
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
FAKE_UPSTREAM_CHECKER.version = "0.9"
FAKE_UPSTREAM_CHECKER.extra_info = "Test information"
FAKE_UPSTREAM_CHECKER.timeout = 30
FAKE_UPSTREAM_CHECKER.get_version.return_value = "1.0"


FAKE_VERSION_INFO_WITH_CHECKER = {
    "version": 1.1,
    "source": FAKE_UPSTREAM_CHECKER,
    "tags": set(["latest", "latest-stable"]),
    "updated": datetime(2020, 3, 3, 13, 37,),
}
