import json
import logging
from abc import ABCMeta, abstractmethod
import pathlib

__name__ = "checker"
NO_VERSION = "undefined"


class UpstreamChecker(metaclass=ABCMeta):
    def __init__(self, path: pathlib.Path):
        self.uri: str = ""
        self.author: str = ""
        self.tool: str = ""
        self.provider: str = ""
        self.method: str = ""
        self.version: str = ""
        self.extra_info: str = ""
        self.logger = logging.getLogger(__name__)
        self.initToolObject(path)

    def initToolObject(self, path: pathlib.Path):
        with open(path, "r") as f:
            tool_info = json.load(f)
            self.uri = tool_info.get("uri", "")
            self.author = tool_info.get("author", "")
            self.tool = tool_info.get("tool", "")
            self.provider = tool_info.get("provider", "")
            self.method = tool_info.get("method", "")

            if not self.uri or not (self.author and self.tool and self.provider):
                raise ValueError(
                    f"Either URI or author, tool and provider must be provided for upstream check for tool {self.tool}."
                )
            self.logger.info(f"Instancing tool {self.tool}")

    @abstractmethod
    def get_version(self):
        pass
