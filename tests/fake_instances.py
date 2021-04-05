# from unittest.mock import Mock
# from ..cincanregistry.toolinfo import VersionInfo
# from ..cincanregistry.checkers import *

# def get_fake_VersionInfo():

#     ret = VersionInfo(1.1, set(["latest", "latest-stable"]))
#     return

# def get_fake_GithubChecker():

#     checker = GitHubChecker()

#     return
import docker
from datetime import datetime
from unittest import mock
from cincanregistry.checkers import UpstreamChecker
from cincanregistry import VersionType
from copy import deepcopy

TEST_REPOSITORY = "cincan/test"

FAKE_VERSION_INFO_NO_CHECKER = {
    "version": "0.9",
    "version_type": VersionType.REMOTE,
    "source": "no_checker_case",
    "tags": {"latest", "latest-stable"},
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
    "version_type": VersionType.UPSTREAM,
    "source": FAKE_UPSTREAM_CHECKER,
    "tags": {"latest", "latest-stable"},
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

FAKE_DOCKER_REGISTRY_ERROR = {
    "errors": [{"message": "Big error...", "code": 400, "detail": "This is why!"}]
}

# Manifest Schema v1
FAKE_IMAGE_ATTRS = {
    "Architecture": "amd64",
    "Author": "",
    "Comment": "",
    "Config": {
        "AttachStderr": False,
        "AttachStdin": False,
        "AttachStdout": False,
        "Cmd": ["echo", "Hello, world!"],
        "Domainname": "",
        "Entrypoint": None,
        "Env": [
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "TOOL_VERSION=1.0",
        ],
        "Hostname": "",
        "Image": "sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4",
        "Labels": {"MAINTAINER": "cincan.io"},
        "OnBuild": None,
        "OpenStdin": False,
        "StdinOnce": False,
        "Tty": False,
        "User": "",
        "Volumes": None,
        "WorkingDir": "",
    },
    "Container": "6e470d761c29de22781774ab9ab5e16678f1a603ba2f5c0a6b83c8597bd63b7a",
    "ContainerConfig": {
        "AttachStderr": False,
        "AttachStdin": False,
        "AttachStdout": False,
        "Cmd": ["/bin/sh", "-c", "#(nop) ", 'CMD ["echo" "Hello, world!"]'],
        "Domainname": "",
        "Entrypoint": None,
        "Env": [
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "TOOL_VERSION=1.0",
        ],
        "Hostname": "6e470d761c29",
        "Image": "sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4",
        "Labels": {"MAINTAINER": "cincan.io"},
        "OnBuild": None,
        "OpenStdin": False,
        "StdinOnce": False,
        "Tty": False,
        "User": "",
        "Volumes": None,
        "WorkingDir": "",
    },
    "Created": "2020-05-23T19:43:14.106177342Z",
    "DockerVersion": "19.03.8-ce",
    "GraphDriver": {
        "Data": {
            "MergedDir": "/var/lib/docker/overlay2/f319a3146696a2a621e15ecad735c9c3ce35e0b7b7c3435e6e5720d3b71efb3d/merged",
            "UpperDir": "/var/lib/docker/overlay2/f319a3146696a2a621e15ecad735c9c3ce35e0b7b7c3435e6e5720d3b71efb3d/diff",
            "WorkDir": "/var/lib/docker/overlay2/f319a3146696a2a621e15ecad735c9c3ce35e0b7b7c3435e6e5720d3b71efb3d/work",
        },
        "Name": "overlay2",
    },
    "Id": "sha256:50ed6209f1ea728d82faf55a19d19eb00598dd0c27c06e6b077bb99f32b010b0",
    "Metadata": {"LastTagTime": "2020-05-23T22:43:15.020481547+03:00"},
    "Os": "linux",
    "Parent": "sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4",
    "RepoDigests": [
        "cincan/test@sha256:4bbeb2cdf0df6ceca11c1b404a818d0839e6044338cd89fa379119c86c832e71"
    ],
    "RepoTags": ["cincan/test:latest"],
    "RootFS": {
        "Layers": [
            "sha256:5216338b40a7b96416b8b9858974bbe4acc3096ee60acbc4dfb1ee02aecceb10"
        ],
        "Type": "layers",
    },
    "Size": 5591300,
    "VirtualSize": 5591300,
}
FAKE_IMAGE_ATTRS2 = deepcopy(FAKE_IMAGE_ATTRS)
# Typo in env TOOL_VERSION
FAKE_IMAGE_ATTRS2["Config"]["Env"] = [
    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "TOOL_VERSIO=0.9",
]

FAKE_IMAGE = mock.Mock(spec=docker.models.images.Image)
FAKE_IMAGE.attrs = FAKE_IMAGE_ATTRS
FAKE_IMAGE.tags = ["cincan/test:latest"]
FAKE_IMAGE2 = mock.Mock(spec=docker.models.images.Image)
FAKE_IMAGE2.attrs = FAKE_IMAGE_ATTRS
FAKE_IMAGE2.tags = ["cincan/test:dev"]
FAKE_IMAGE3 = mock.Mock(spec=docker.models.images.Image)
FAKE_IMAGE3.attrs = FAKE_IMAGE_ATTRS2
FAKE_IMAGE3.tags = ["cincan/test:test"]

# Deprecated v1 manifest - not used anymore
FAKE_MANIFEST = {
    "architecture": "amd64",
    "fsLayers": [
        {
            "blobSum": "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
        },
        {
            "blobSum": "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
        },
        {
            "blobSum": "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
        },
        {
            "blobSum": "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
        },
        {
            "blobSum": "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
        },
        {
            "blobSum": "sha256:c9b1b535fdd91a9855fb7f82348177e5f019329a58c53c47272962dd60f71fc9"
        },
    ],
    "history": [
        {
            "v1Compatibility": '{"architecture":"amd64","config":{"Hostname":"","Domainname":"","User":"","AttachStdin":false,"AttachStdout":false,"AttachStderr":false,"Tty":false,"OpenStdin":false,"StdinOnce":false,"Env":["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","TOOL_VERSION=1.0"],"Cmd":["echo","Hello, '
            'world!"],"Image":"sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4","Volumes":null,"WorkingDir":"","Entrypoint":null,"OnBuild":null,"Labels":{"MAINTAINER":"cincan.io"}},"container":"6e470d761c29de22781774ab9ab5e16678f1a603ba2f5c0a6b83c8597bd63b7a","container_config":{"Hostname":"6e470d761c29","Domainname":"","User":"","AttachStdin":false,"AttachStdout":false,"AttachStderr":false,"Tty":false,"OpenStdin":false,"StdinOnce":false,"Env":["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","TOOL_VERSION=1.0"],"Cmd":["/bin/sh","-c","#(nop) '
            '","CMD [\\"echo\\" \\"Hello, '
            'world!\\"]"],"Image":"sha256:bc2af71e72403fbbcf777d551de96ffbcdc2837875370fc77c18befa895097d4","Volumes":null,"WorkingDir":"","Entrypoint":null,"OnBuild":null,"Labels":{"MAINTAINER":"cincan.io"}},"created":"2020-05-23T19:43:14.106177342Z","docker_version":"19.03.8-ce","id":"5dfc05a56cc5819bb4dec3f7d19f908566c4d115457a1be8cc02ca87cc8d81c0","os":"linux","parent":"7099d9ed2d5fca9f9a65e010826d70a5fd5c53d64a5590292a89e106f8f98d6d","throwaway":true}'
        },
        {
            "v1Compatibility": '{"id":"7099d9ed2d5fca9f9a65e010826d70a5fd5c53d64a5590292a89e106f8f98d6d","parent":"015cf255964c759a51ea696916c8f112e6d0a7968859b1fafd243d9247f6648f","created":"2020-05-23T19:43:13.801013161Z","container_config":{"Cmd":["/bin/sh '
            '-c echo \\"Hello, '
            'world!\\""]},"throwaway":true}'
        },
        {
            "v1Compatibility": '{"id":"015cf255964c759a51ea696916c8f112e6d0a7968859b1fafd243d9247f6648f","parent":"1f470a89b4bfd6e3558e340359062e86485fed5fbaaa3d4e0c7d9b3de5910cc5","created":"2020-05-23T19:43:13.03913518Z","container_config":{"Cmd":["/bin/sh '
            "-c #(nop)  ENV "
            'TOOL_VERSION=1.0"]},"throwaway":true}'
        },
        {
            "v1Compatibility": '{"id":"1f470a89b4bfd6e3558e340359062e86485fed5fbaaa3d4e0c7d9b3de5910cc5","parent":"4698bdfdf9a50584d768f267df5ea06575733809413b4aa30f526d1c8442ee4c","created":"2020-04-16T22:37:19.783297733Z","container_config":{"Cmd":["/bin/sh '
            "-c #(nop)  LABEL "
            'MAINTAINER=cincan.io"]},"throwaway":true}'
        },
        {
            "v1Compatibility": '{"id":"4698bdfdf9a50584d768f267df5ea06575733809413b4aa30f526d1c8442ee4c","parent":"2ff09547bf97be635cf104ec0ff3033b8c103a04e01a3d2e1f84f07dfb5cd80c","created":"2020-01-18T01:19:37.187497623Z","container_config":{"Cmd":["/bin/sh '
            "-c #(nop)  CMD "
            '[\\"/bin/sh\\"]"]},"throwaway":true}'
        },
        {
            "v1Compatibility": '{"id":"2ff09547bf97be635cf104ec0ff3033b8c103a04e01a3d2e1f84f07dfb5cd80c","created":"2020-01-18T01:19:37.02673981Z","container_config":{"Cmd":["/bin/sh '
            "-c #(nop) ADD "
            "file:e69d441d729412d24675dcd33e04580885df99981cec43de8c9b24015313ff8e "
            'in / "]}}'
        },
    ],
    "name": "cincan/test",
    "schemaVersion": 1,
    "signatures": [
        {
            "header": {
                "alg": "ES256",
                "jwk": {
                    "crv": "P-256",
                    "kid": "XXJM:6UZG:AND7:DMOA:ZLVC:VRTJ:NZVX:OFEI:PTMN:APDF:GULV:ELAG",
                    "kty": "EC",
                    "x": "7Rq4ad1-iEAq9o-6LxPGGYJ6t25wrHfxFQioZ4zvO9U",
                    "y": "Ir-FTF3YyuEdG-M3sgfS4EQ7N_4M_zes5fQasc7haQQ",
                },
            },
            "protected": "eyJmb3JtYXRMZW5ndGgiOjQwNjUsImZvcm1hdFRhaWwiOiJDbjAiLCJ0aW1lIjoiMjAyMC0wNS0yM1QyMDoyODo1N1oifQ",
            "signature": "6qA-GHZ21iaxVOtNHJwoVp_2JdDWuahoUsHP0-Nfi--PvcTRb_gXl9UM_MYRQIwCyXI3ukvs1R_oKB8k5j8JMg",
        }
    ],
    "tag": "latest",
}

GITLAB_FAKE_META_DICT = {
    "file_name": "meta.json",
    "file_path": "radare2/meta.json",
    "size": 254,
    "encoding": "base64",
    "content_sha256": "f9f2fe65e99c313d2637530f09176fc246d9ce4d3e69d40ead17aaf772c8fbe0",
    "ref": "master",
    "blob_id": "babe8e938c676c81eb6b2308159481db3f955c33",
    "commit_id": "0fcb693be9375c88ed5170c0770a8d72a6e9017e",
    "last_commit_id": "356d07c779bd09482ddf2d4078b81fabc97e2f2d",
    "content": "ewogICJ1cHN0cmVhbXMiOiBbCiAgICB7CiAgICAgICJ1cmkiOiAiaHR0cHM6Ly9naXRodWIuY29tL3JhZGFyZW9yZy9yYWRhcmUyLyIsCiAgICAgICJyZXBvc2l0b3J5IjogInJhZGFyZW9yZyIsCiAgICAgICJ0b29sIjogInJhZGFyZTIiLAogICAgICAicHJvdmlkZXIiOiAiR2l0SHViIiwKICAgICAgIm1ldGhvZCI6ICJyZWxlYXNlIiwKICAgICAgIm9yaWdpbiI6IHRydWUsCiAgICAgICJkb2NrZXJfb3JpZ2luIjogdHJ1ZQogICAgfQogIF0KfQo=",
}
