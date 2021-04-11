import logging
import re
from abc import ABCMeta, abstractmethod
from typing import List, Dict

import requests
from requests.exceptions import Timeout, ConnectionError

NO_VERSION = "Not found"
__name__ = "checker"


class UpstreamChecker(metaclass=ABCMeta):
    def __init__(
            self, tool_info: dict, token: str = "", timeout=20, version="", extra_info=""
    ):
        self.uri: str = tool_info.get("uri", "")
        self.repository: str = tool_info.get("repository", "")
        self.tool: str = tool_info.get("tool", "")
        self.provider: str = tool_info.get("provider", "")
        self.method: str = tool_info.get("method", "")
        self.suite: str = tool_info.get("suite", "")
        self.origin: bool = tool_info.get("origin", False)
        if not isinstance(self.origin, bool) and (self.origin not in [0, 1]):
            raise ValueError(f"Origin value is not boolean. Value: {self.origin}")
        self.docker_origin: bool = tool_info.get("docker_origin", False)
        if not isinstance(self.docker_origin, bool) and (self.docker_origin not in [0, 1]):
            raise ValueError(f"Docker origin value is not boolean. Value {self.docker_origin}")
        self.version: str = version
        self.extra_info: str = extra_info
        self.token: str = token
        self.logger = logging.getLogger(__name__)
        self.timeout: int = timeout

        if not (self.uri or (self.repository and self.tool and self.provider)):
            raise ValueError(
                f"Either URI or repository, tool and provider must be provided for upstream check for tool {self.tool}."
            )
        self.logger.debug(f"Instancing tool {self.tool}")

    def __str__(self) -> str:
        """Return provider name in lowercase, in case called as string format"""
        return self.provider.lower()

    __repr__ = __str__

    def __iter__(self):
        yield "uri", self.uri,
        yield "repository", self.repository,
        yield "tool", self.tool,
        yield "provider", self.provider,
        yield "method", self.method,
        yield "suite", self.suite,
        yield "origin", self.origin,
        yield "docker_origin", self.docker_origin
        yield "version", self.version,
        yield "extra_info", self.extra_info

    def __del__(self):
        if hasattr(self, "logger"):
            self.logger.debug(
                f"Tool {self.tool} has updated upstream version information of {self.version}"
            )

    def _fail(self, r: requests.Response = None):
        """
        Set version for not defined on fail, log error.
        """
        self.version = NO_VERSION
        self.logger.error(f"Failed to fetch version update information for {self.tool}.")

    def _sort_latest_tag(self, versions: List[dict], tag_key: str) -> Dict:
        """
        Removes all non-digits and non-dots from value in list of dictionaries,
        as in attempt of normalizing version numbers.
        Split versions by dot to generate map, sort.
        Returns whole dictionary with potentially latest tag.
        """
        return next(
            iter(
                sorted(
                    versions,
                    reverse=True,
                    key=lambda s: list(
                        map(
                            int,
                            filter(None, re.sub(r"[^0-9.]+", "", s.get(tag_key), re.I).split(".")),
                        )
                    )
                    if "." in s.get(tag_key)
                    else [-1],
                )
            )
        )

    def get_version(self, curr_ver: str = "") -> str:
        try:
            self._get_version(curr_ver)
        except Timeout:
            self.logger.error(
                f"Connection timed out for tool {self.tool} when checking upstream with {self.provider}."
            )
            self.version = NO_VERSION
        except ConnectionError:
            self.logger.error(
                f"Failed to connect provider {self.provider} of tool {self.tool} when checking upstream. Is "
                f"configuration correct? "
            )
            self.version = NO_VERSION
        return self.version

    @abstractmethod
    def _get_version(self, curr_ver: str = ""):
        pass
