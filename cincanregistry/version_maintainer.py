from typing import Dict, List
from .tool_info import ToolInfo
from .version_info import VersionInfo
from .checkers import classmap
from concurrent.futures import ThreadPoolExecutor
import pathlib
import json
import datetime
import logging
import asyncio


class VersionMaintainer:
    """
    Class for getting possible new versions for tools in ToolRegistry
    """

    def __init__(
        self,
        tokens: dict = None,
        prefix: str = "cincan/",
        meta_filename: str = "meta.json",
        metafiles_location: str = "",
    ):
        self.logger = logging.getLogger("versions")
        self.configuration = tokens or {}
        self.max_workers = 30
        # prefix, mostly meaning the owner of possible Docker image
        self.prefix = prefix
        self.meta_filename = meta_filename
        self.metafiles_location = pathlib.Path(metafiles_location) or pathlib.Path.home() / ".cincan" / "tools"
        self.able_to_check = self.get_available_checkers()

    def get_available_checkers(self) -> Dict:
        """
        Gets dictionary of tools, whereas upstream/origin check is supported.

        """

        able_to_check = {}
        for tool_path in self.metafiles_location.iterdir():
            able_to_check[f"{self.prefix}{tool_path.stem}"] = tool_path
        if not able_to_check:
            self.logger.error(
                f"No single configuration for upstream check found. Something is wrong in path {self.metafiles_location}"
            )
        return able_to_check

    async def get_versions_single_tool(
        self, tool: str, local_tools: dict, remote_tools: dict
    ):
        l_tool = local_tools.get(tool, "")
        r_tool = remote_tools.get(tool, "")
        if l_tool or r_tool:
            tool_path = self.able_to_check.get(tool)
            if not tool_path:
                raise FileNotFoundError(f"Upstream check not implemented for {tool}.")
            if r_tool:
                self._set_single_tool_upstream_versions(tool_path, r_tool)
            else:
                self._set_single_tool_upstream_versions(tool_path, l_tool)
        else:
            raise FileNotFoundError(f"Given tool {tool} not found locally or remotely.")
        return l_tool, r_tool

    def _set_single_tool_upstream_versions(self, tool_path: str, tool: ToolInfo) -> str:

        self.logger.info(
            f"Updating origin version information for tool {tool.name:<{40}}\r\r"
        )
        with open(tool_path / self.meta_filename) as f:
            conf = json.load(f)
            # Expect list or single object in "upstreams" value
            for tool_info in (
                conf.get("upstreams")
                if isinstance(conf.get("upstreams"), List)
                else [conf.get("upstreams")]
            ):
                provider = tool_info.get("provider").lower()
                token_provider = tool_info.get("token_provider") or provider
                token = (
                    self.configuration.get(token_provider) if self.configuration else ""
                )
                if provider not in classmap.keys():
                    self.logger.error(
                        f"No upstream checker implemented for tool '{tool.name}' with provider '{provider}'. Check JSON configuration."
                    )
                    continue
                upstream_info = classmap.get(provider)(tool_info, token)
                tool.upstream_v.append(
                    VersionInfo(
                        upstream_info.get_version(),
                        upstream_info,
                        set({"latest"}),
                        datetime.datetime.now(),
                        origin=upstream_info.origin,
                    )
                )

    async def _check_upstream_versions(self, tools: List):
        """
        Checks for available versions in upstream
        """
        tasks = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for t in tools:
                tool_path = self.able_to_check.get(t)
                if tool_path:
                    tool = tools.get(t)
                    loop = asyncio.get_event_loop()
                    tasks.append(
                        loop.run_in_executor(
                            executor,
                            self._set_single_tool_upstream_versions,
                            *(tool_path, tool),
                        )
                    )
                else:
                    self.logger.debug(f"Upstream check not implemented for tool {t}")
            if tasks:
                for response in await asyncio.gather(*tasks):
                    pass
            else:
                self.logger.warning(
                    "No known methods to get updates for any of the local tools."
                )
        return tools

    async def _list_versions_single(self, l_tool: ToolInfo, r_tool: ToolInfo) -> dict:
        """
        Generates version information for single tool. Attempts to define if there are
        new versions available.
        """
        tool_info = {}
        tool_info["name"] = r_tool.name if r_tool else l_tool.name
        tool_info["versions"] = {}
        tool_info["versions"]["local"] = {
            "version": l_tool.getLatest().version if l_tool else ""
        }
        tool_info["versions"]["remote"] = {"version": r_tool.getLatest().version}

        r_tool_orig = r_tool.getOriginVersion()
        if not r_tool_orig.provider:
            r_tool_orig = r_tool.getDockerOriginVersion()

        tool_info["versions"]["origin"] = {"version": r_tool_orig.version}
        tool_info["versions"]["origin"]["details"] = (
            dict(r_tool_orig.source)
            if r_tool_orig.origin or r_tool_orig.docker_origin
            else ""
        )

        tool_info["versions"]["other"] = [
            {
                "version": v.version,
                "details": dict(v.source)
                if not isinstance(v.source, str)
                else v.source,
            }
            for v in r_tool.upstream_v
            if not v.origin and v.source
        ]
        tool_info["updates"] = {}

        # Compare all versions, if there are updates available #

        # Compare local to remote at first
        if l_tool:
            if l_tool.getLatest() == r_tool.getLatest():
                tool_info["updates"]["local"] = False
            else:
                tool_info["updates"]["local"] = True

        # Remote to upstream
        r_latest = r_tool.getLatest()
        r_up_latest = r_tool.getLatest(in_upstream=True)
        tool_info["updates"]["remote"] = False

        if (r_latest and r_up_latest) and r_latest == r_up_latest:
            # Up to date with latest upstream version
            pass
        elif r_latest.version == "undefined" or (
            tool_info.get("versions").get("origin").get("version") == "Not implemented"
            and not tool_info.get("other_versions")
        ):
            pass
        # elif r_latest in [v for v in r_tool.upstream_v if not v.origin]:
        #     pass
        else:
            self.logger.debug(
                f"Tool {r_tool.name} is not up to date with origin/installation upstream."
            )
            tool_info["updates"]["remote"] = True

        return tool_info
