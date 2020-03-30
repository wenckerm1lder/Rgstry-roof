import logging
import re
from abc import ABCMeta, abstractmethod

__name__ = "checker"
NO_VERSION = "undefined"


class UpstreamChecker(metaclass=ABCMeta):
    def __init__(self, tool_info: dict, token: str = ""):
        self.uri: str = tool_info.get("uri", "")
        self.author: str = tool_info.get("author", "")
        self.tool: str = tool_info.get("tool", "")
        self.provider: str = tool_info.get("provider", "")
        self.method: str = tool_info.get("method", "")
        self.version: str = ""
        self.extra_info: str = ""
        self.token: str = token
        self.logger = logging.getLogger(__name__)

        if not self.uri or not (self.author and self.tool and self.provider):
            raise ValueError(
                f"Either URI or author, tool and provider must be provided for upstream check for tool {self.tool}."
            )
        self.logger.debug(f"Instancing tool {self.tool}")

    def _fail(self):
        """
        Set version for not defined on fail, log error.
        """
        self.version = NO_VERSION
        self.logger.error(f"Failed to fetch version update information for {self.tool}")

    def _sort_latest_tag(self, versions, name: str = ""):
        """
        Removes all letters, hyphens and dashes from list of strings,
        as in attempt of normalizing version numbers.
        """
        return next(
            iter(
                sorted(
                    versions,
                    reverse=True,
                    key=lambda s: list(
                        map(
                            int,
                            re.sub(r"[a-zA-Z-_]+", "", s.get(name), re.I).split("."),
                        )
                    ),
                )
            )
        )

    @abstractmethod
    def get_version(self, curr_ver: str = ""):
        pass
