import logging
from abc import ABCMeta, abstractmethod

__name__ = "checker"
NO_VERSION = "undefined"


class UpstreamChecker(metaclass=ABCMeta):
    def __init__(self, tool_info: dict):
        self.uri: str = tool_info.get("uri", "")
        self.author: str = tool_info.get("author", "")
        self.tool: str = tool_info.get("tool", "")
        self.provider: str = tool_info.get("provider", "")
        self.method: str = tool_info.get("method", "")
        self.version: str = ""
        self.extra_info: str = ""
        self.logger = logging.getLogger(__name__)

        if not self.uri or not (self.author and self.tool and self.provider):
            raise ValueError(
                f"Either URI or author, tool and provider must be provided for upstream check for tool {self.tool}."
            )
        self.logger.debug(f"Instancing tool {self.tool}")

    @abstractmethod
    def get_version(self, curr_ver: str = ""):
        pass
