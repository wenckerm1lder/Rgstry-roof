# from unittest.mock import Mock
# from ..cincanregistry.toolinfo import VersionInfo
# from ..cincanregistry.checkers import *

# def get_fake_VersionInfo():

#     ret = VersionInfo(1.1, set(["latest", "latest-stable"]))
#     return

# def get_fake_GithubChecker():

#     checker = GitHubChecker()

#     return
from datetime import datetime
from unittest import mock
from cincanregistry.checkers import UpstreamChecker


FAKE_VERSION_INFO_NO_CHECKER = {
    "version": 0.9,
    "source": "no_checker_case",
    "tags": set(["latest", "latest-stable"]),
    "updated": datetime(2020, 3, 3, 13, 37,),
    "size": 39529754,
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
FAKE_UPSTREAM_CHECKER.get_version = mock.Mock(
    UpstreamChecker, return_value="1.2", auto_spec=True,
)
# FAKE_UPSTREAM_CHECKER.get_version.return_value = "1.2"
FAKE_UPSTREAM_CHECKER.__iter__ = UpstreamChecker.__iter__

FAKE_VERSION_INFO_WITH_CHECKER = {
    "version": 0.9,
    "source": FAKE_UPSTREAM_CHECKER,
    "tags": set(["latest", "latest-stable"]),
    "updated": datetime(2020, 3, 3, 13, 37,),
    "size": 3952975,
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

FAKE_IMAGE_ATTRS = {
    "Id": "sha256:c37a27619b376487d2b0b064112441c46aa1f6089440743f34177aa6abd30abd",
    "RepoTags": [
        "cincan/feature_extractor:latest-stable",
        "test_feature_extractor:latest",
    ],
    "RepoDigests": [],
    "Parent": "sha256:4fdf99d8fd2b72ae9f9e61521aa2379e92a941a0e8f335c367a66ca2dd7aab4a",
    "Comment": "",
    "Created": "2020-05-19T14:12:28.387116842Z",
    "Container": "e75fa5d75d67a71b3a58a84dac97ab6c120ef883176a3ee695acd1c76e823c9d",
    "ContainerConfig": {
        "Hostname": "e75fa5d75d67",
        "Domainname": "",
        "User": "appuser",
        "AttachStdin": False,
        "AttachStdout": False,
        "AttachStderr": False,
        "Tty": False,
        "OpenStdin": False,
        "StdinOnce": False,
        "Env": [
            "PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG=C.UTF-8",
            "GPG_KEY=0D96DF4D4110E5C43FBFB17F2D347EA6AA65421D",
            "PYTHON_VERSION=3.6.10",
            "PYTHON_PIP_VERSION=20.1",
            "PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/1fe530e9e3d800be94e04f6428460fc4fb94f5a9/get-pip.py",
            "PYTHON_GET_PIP_SHA256=ce486cddac44e99496a702aa5c06c5028414ef48fdfd5242cd2fe559b13d4348",
            "TOOL_VERSION=0.2",
        ],
        "Cmd": ["/bin/sh", "-c", "#(nop) ", 'CMD ["-h"]'],
        "Image": "sha256:4fdf99d8fd2b72ae9f9e61521aa2379e92a941a0e8f335c367a66ca2dd7aab4a",
        "Volumes": None,
        "WorkingDir": "/home/appuser",
        "Entrypoint": [
            "/usr/local/bin/python",
            "/feature_extractor/analyze_parallel.py",
            "--confpath",
            "/feature_extractor",
        ],
        "OnBuild": None,
        "Labels": {"MAINTAINER": "cincan.io"},
    },
    "DockerVersion": "19.03.8-ce",
    "Author": "",
    "Config": {
        "Hostname": "",
        "Domainname": "",
        "User": "appuser",
        "AttachStdin": False,
        "AttachStdout": False,
        "AttachStderr": False,
        "Tty": False,
        "OpenStdin": False,
        "StdinOnce": False,
        "Env": [
            "PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG=C.UTF-8",
            "GPG_KEY=0D96DF4D4110E5C43FBFB17F2D347EA6AA65421D",
            "PYTHON_VERSION=3.6.10",
            "PYTHON_PIP_VERSION=20.1",
            "PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/1fe530e9e3d800be94e04f6428460fc4fb94f5a9/get-pip.py",
            "PYTHON_GET_PIP_SHA256=ce486cddac44e99496a702aa5c06c5028414ef48fdfd5242cd2fe559b13d4348",
            "TOOL_VERSION=0.2",
        ],
        "Cmd": ["-h"],
        "Image": "sha256:4fdf99d8fd2b72ae9f9e61521aa2379e92a941a0e8f335c367a66ca2dd7aab4a",
        "Volumes": None,
        "WorkingDir": "/home/appuser",
        "Entrypoint": [
            "/usr/local/bin/python",
            "/feature_extractor/analyze_parallel.py",
            "--confpath",
            "/feature_extractor",
        ],
        "OnBuild": None,
        "Labels": {"MAINTAINER": "cincan.io"},
    },
    "Architecture": "amd64",
    "Os": "linux",
    "Size": 533065388,
    "VirtualSize": 533065388,
    "GraphDriver": {
        "Data": {
            "LowerDir": "/var/lib/docker/overlay2/1196ff5152eb65b5b5c9dcf252f0c960575696ad706b74587129f19d9a9097f8/diff:/var/lib/docker/overlay2/6ea4d653c4043660f398c2dd04fa24c8a2cb61644e3bfd8a4314c0b9702bb377/diff:/var/lib/docker/overlay2/d55b721b77e5884a95580b83036fefb59d53a94124decb33e5554b7e1cffcfb6/diff:/var/lib/docker/overlay2/7288c7fdcc776cc5d3d668b23246713c39bd80b1ac34018f9f47cdf7fbb4642d/diff:/var/lib/docker/overlay2/fc1ca497292c70c2741fb2d27d8ee7f26496c00689832a02904a74dc0896147b/diff",
            "MergedDir": "/var/lib/docker/overlay2/cac3e1ca7ec9006a4cd0eb2688ec124d6ea8f022f4f652038cafe9978c9ce50a/merged",
            "UpperDir": "/var/lib/docker/overlay2/cac3e1ca7ec9006a4cd0eb2688ec124d6ea8f022f4f652038cafe9978c9ce50a/diff",
            "WorkDir": "/var/lib/docker/overlay2/cac3e1ca7ec9006a4cd0eb2688ec124d6ea8f022f4f652038cafe9978c9ce50a/work",
        },
        "Name": "overlay2",
    },
    "RootFS": {
        "Type": "layers",
        "Layers": [
            "sha256:ffc9b21953f4cd7956cdf532a5db04ff0a2daa7475ad796f1bad58cfbaf77a07",
            "sha256:1bd26e8168dc6dc2769356b72ef718252f5378c06a25928933f30be3e6354720",
            "sha256:a0fa4fb24916cbdb8712d65409bfc6b185946716cc57e06deb6b01f4e05706f8",
            "sha256:38ae98837e8488a6101828d7bcc6fbec0feb50bedb6106fa4fd6ec9976e2b2db",
            "sha256:fdb6eb5e240033dd460d624b4238d64846c24b0e6ff1242ee989916276637817",
            "sha256:09da5ff754e024e99003e233c7a99d2e09e7e140a788dcb287dca0180b936746",
        ],
    },
    "Metadata": {"LastTagTime": "2020-05-19T17:13:16.665036311+03:00"},
}

