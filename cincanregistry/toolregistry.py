import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from os.path import basename
from typing import Tuple, Dict

from cincanregistry import ToolInfo, VersionMaintainer, Remotes
from cincanregistry.remotes import DockerHubRegistry, QuayRegistry
from ._registry import RegistryBase
from .daemon import DaemonRegistry


class ToolRegistry(RegistryBase):
    """
    A tool registry
    Creates combined total registry from local and remote tools

    """

    def __init__(
            self,
            *args,
            default_remote: Remotes = None,
            silent: bool = False,
            **kwargs,

    ):
        super(ToolRegistry, self).__init__(*args)
        self.logger: logging.Logger = logging.getLogger("registry")
        self.default_remote = default_remote if (
                default_remote is not None and default_remote != list(Remotes)[0]) else self.config.registry
        self.local_registry = DaemonRegistry(*args, silent=silent, **kwargs)
        if self.default_remote == Remotes.QUAY:
            self.remote_registry = QuayRegistry(*args, **kwargs)
        elif self.default_remote == Remotes.DOCKERHUB:
            self.remote_registry = DockerHubRegistry(*args, **kwargs)
        else:
            self.logger.error(f"Unsupported remote registry: {self.default_remote}")
            exit(1)
        if not self.config.namespace:
            self.config.namespace = self.remote_registry.cincan_namespace

    async def get_local_remote_tools(self, defined_tag: str = "") -> Tuple[Dict, Dict]:
        """
        Get remote and local tools in parallel to increase performance
        """
        tasks = [
            self.local_registry.get_tools(defined_tag, prefix=self.remote_registry.full_prefix),
            self.remote_registry.get_tools(defined_tag),
        ]
        local_tools, remote_tools = await asyncio.ensure_future(asyncio.gather(*tasks))
        return local_tools, remote_tools

    def get_tools(self, defined_tag: str = "", merge=True) -> Dict[str, ToolInfo]:
        """List all tools"""
        loop = asyncio.get_event_loop()
        local_tools, remote_tools = loop.run_until_complete(
            self.get_local_remote_tools(defined_tag)
        )
        loop.close()
        use_tools = {}
        # merged_tools_dic = {**local_tools, **remote_tools}
        for i in set().union(local_tools.keys(), remote_tools.keys()):

            size = ""
            l_version = ""
            r_version = ""
            if defined_tag:
                l_tool = local_tools.get(i, None)
                r_tool = remote_tools.get(i, None)
                if l_tool:
                    for ver in l_tool.versions:
                        if defined_tag in ver.tags:
                            l_version = ver.version
                            break
                    if not l_version:
                        f"Provided tag '{defined_tag}' not found for local image {i}."
                if r_tool:
                    ver = r_tool.get_latest(in_remote=True)
                    if ver:
                        r_version = ver.version
                        # Add size based on remote version
                        # compressed
                        size = ver.size
                    if not r_version:
                        f"Provided tag '{defined_tag}' not found for remote image {i}."
                if not r_version and not l_version:
                    continue
                if not l_version:
                    l_version = "Not installed"
            else:
                l_version = (
                    local_tools.get(i).get_latest().version if local_tools.get(i) else ""
                )
                r_obj = remote_tools.get(i).get_latest(in_remote=True) if remote_tools.get(i) else None
                if r_obj:
                    r_version = r_obj.version
                    size = r_obj.size
                else:
                    r_version = ""

            use_tools[i] = {}
            use_tools[i]["local_version"] = l_version
            use_tools[i]["remote_version"] = r_version
            # Local has no description
            use_tools[i]["description"] = (
                remote_tools.get(i).description if remote_tools.get(i) else ""
            )
            use_tools[i]["compressed_size"] = size
        if not use_tools:
            self.logger.info(f"No single tool found with tag `{defined_tag}`.")
        return use_tools

    async def list_versions(
            self,
            tool: str = "",
            to_json: bool = False,
            only_updates: bool = False,
            force_refresh: bool = False,
    ):
        maintainer = VersionMaintainer(
            self.config,
            db=self.db,
            force_refresh=force_refresh,
        )
        versions = {}
        if tool:
            if "/" in tool:
                self.logger.error("Give only name of the tool, without prefixes or namespaces related to tool image."
                                  f" Tool must be in default registry: {self.default_remote}.")
                sys.exit(1)
            tool_name = basename(tool)
            # tool_with_namespace = f"{self.remote_registry.full_prefix}/{tool_name}"
            l_tool = self.local_registry.create_local_tool_info_by_name(tool_name)
            r_tool = self.remote_registry.read_remote_versions_from_db(tool_name) if not force_refresh else {}

            now = datetime.now()
            if not r_tool:
                r_tool = ToolInfo(tool_name, datetime.min, self.remote_registry.registry_name)
            if not r_tool.updated or not (
                    now - timedelta(hours=self.config.cache_lifetime) <= r_tool.updated <= now
            ):
                self.remote_registry.fetch_tags(r_tool, update_cache=True)
            if l_tool or (r_tool and not r_tool.updated == datetime.min):
                l_tool, r_tool = maintainer.get_versions_single_tool(
                    tool_name, l_tool, r_tool
                )
                versions = await maintainer.list_versions_single(
                    l_tool, r_tool, only_updates
                )
            else:
                raise FileNotFoundError(
                    f"Given tool {tool} not found locally or remotely. Please, give only the basename of the tool,"
                    f"without prefixes."
                )
        else:
            remote_tools = await self.remote_registry.get_tools(force_update=force_refresh)
            # Remote tools, with included upstream version information
            remote_tools_with_origin_version = await maintainer.check_upstream_versions(
                remote_tools
            )
            # Local tools, without checking and corresponding the configured registry
            local_tools = await self.local_registry.get_tools(prefix=self.remote_registry.full_prefix)
            for t in remote_tools_with_origin_version:
                r_tool = remote_tools_with_origin_version.get(
                    t
                )  # Contains also upstream version info
                l_tool = local_tools.get(t, "")
                t_info = await maintainer.list_versions_single(
                    l_tool, r_tool, only_updates
                )
                if t_info:
                    versions[t] = t_info

        if to_json:
            return json.dumps(versions)
        else:
            return versions
