import logging
import re
from abc import ABCMeta, abstractmethod
from typing import List, Dict
import sys

__name__ = "checker"
NO_VERSION = "Not found"


class UpstreamChecker(metaclass=ABCMeta):
    def __init__(self, tool_info: dict, token: str = ""):
        self.uri: str = tool_info.get("uri", "")
        self.repository: str = tool_info.get("repository", "")
        self.tool: str = tool_info.get("tool", "")
        self.provider: str = tool_info.get("provider", "")
        self.method: str = tool_info.get("method", "")
        self.origin: bool = tool_info.get("origin", "")
        self.version: str = ""
        self.extra_info: str = ""
        self.token: str = token
        self.logger = logging.getLogger(__name__)

        if not (self.uri or self.repository and self.tool and self.provider):
            raise ValueError(
                f"Either URI or repository, tool and provider must be provided for upstream check for tool {self.tool}."
            )
        self.logger.debug(f"Instancing tool {self.tool}")

    def __del__(self):
        self.logger.debug(
            f"Tool {self.tool} has updated upstream version information of {self.version}"
        )

    def _fail(self):
        """
        Set version for not defined on fail, log error.
        """
        self.version = NO_VERSION
        self.logger.error(f"Failed to fetch version update information for {self.tool}")

    def _sort_latest_tag(self, versions: List[dict], tag_key: str = "") -> Dict:
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
                            re.sub(r"[^0-9.]+", "", s.get(tag_key), re.I).split("."),
                        )
                    )
                    if "." in s.get(tag_key)
                    else [-1],
                )
            )
        )

    @abstractmethod
    def get_version(self, curr_ver: str = ""):
        pass
