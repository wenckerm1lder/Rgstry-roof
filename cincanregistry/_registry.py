import logging
import pathlib
from abc import ABCMeta, abstractmethod
from typing import Dict

from cincanregistry import ToolInfo
from cincanregistry.configuration import Configuration
from cincanregistry.database import ToolDatabase


class RegistryBase(metaclass=ABCMeta):
    """
    Base class for local and remote registry

    Provides some methods for handling cache

    # TODO make sqlite3 database instead of JSON...
    """
    VER_UNDEFINED = "undefined"
    CACHE_VERSION_VAR = "__cache_version"
    REMOTE_NAME_VAR = "__registry"

    def __init__(self,
                 config_path: str = "",
                 tools_repo_path: str = "",
                 version_var: str = "TOOL_VERSION",
                 configuration: Configuration = None):
        self.logger: logging.Logger = logging.getLogger("registry")
        self.registry_name: str = ""
        if not configuration:
            self.config: Configuration = Configuration(config_path, tools_repo_path)
        else:
            self.config = configuration
        self.version_var: str = version_var
        self.tool_cache: pathlib.Path = self.config.tool_cache
        self.tool_cache_version: str = self.config.tool_cache_version
        self.tools_repo_path: pathlib.Path = self.config.tools_repo_path
        self.db = ToolDatabase(self.config)

    @abstractmethod
    async def get_tools(self, defined_tag: str = "", force_update: bool = False) -> Dict[str, ToolInfo]:
        pass

    # def read_remote_versions_from_db(
    #         self, tool_name: str = ""
    # ) -> Union[Dict[str, ToolInfo], ToolInfo]:
    #     """
    #     Read the local tool cache file
    #     Returns all as dictionary, or single tool as ToolInfo object
    #     """
    #     r = {}
    #     if tool_name:
    #         return self.db.get_single_tool(tool_name=tool_name)
    #     else:
    #         tools = self.db.get_tools()
    # json.decoder.JSONDecodeError
    # if not self.tool_cache.exists():
    #     return {}
    # r = {}
    # with self.tool_cache.open("r") as f:
    #     try:
    #         root_json = json.load(f)
    #     except json.decoder.JSONDecodeError:
    #         self.logger.warning(
    #             f"Something wrong with '{self.tool_cache.stem}' cache, deleting it ..."
    #         )
    #         self.tool_cache.unlink()
    #         return {}
    #     c_ver = root_json.get(self.CACHE_VERSION_VAR, "")
    #     c_remote = root_json.get(self.REMOTE_NAME_VAR, "")
    #     if not c_ver == self.tool_cache_version or not c_remote == self.registry_name:
    #         self.tool_cache.unlink()
    #         return {}
    #     else:
    #         # These keys make reading hard, ignore them at this point
    #         del root_json[self.CACHE_VERSION_VAR]
    #         del root_json[self.REMOTE_NAME_VAR]
    #     try:
    #         if tool_name:
    #             d = root_json.get(tool_name, {})
    #             return ToolInfo.from_dict(d) if d else {}
    #         for name, j in root_json.items():
    #             r[name] = ToolInfo.from_dict(j)
    #     # If cache is modified to contain extra variables
    #     except TypeError:
    #         self.tool_cache.unlink()
    #         return {}
    # return r
