from typing import Dict, List, Tuple, Union
from .tool_info import ToolInfo
from .version_info import VersionInfo
from .checkers import classmap
from .gitlab_utils import GitLabUtils
from .utils import parse_file_time, format_time
from .configuration import Configuration
from concurrent.futures import ThreadPoolExecutor, as_completed
import pathlib
import json
from datetime import datetime, timedelta
import logging
import asyncio
from .metafiles import MetaHandler


class VersionMaintainer:
    """
    Class for getting possible new versions for tools in ToolRegistry
    """

    def __init__(
            self,
            configuration: Configuration,
            force_refresh: bool = False,
    ):
        self.config = configuration
        self.logger = logging.getLogger("versions")
        self.tokens = self.config.tokens
        # Use local 'tools' path if provided
        self.meta_files_location = self.config.tools_repo_path or self.config.cache_location
        self.meta_filename = self.config.meta_filename
        # Disable download if local path provided
        self.disable_remote_download = (
            self.config.disable_remote if not self.config.tools_repo_path else True
        )

        if self.disable_remote_download:
            self.logger.warning(
                "Remote download disabled for meta files - using local files and they are not updated automatically."
            )
        self.force_refresh = force_refresh
        self.able_to_check = {}
        self.tool_dirs = []

    def _set_available_checkers(self):
        """
        Gets dictionary of tools, whereas upstream/origin check is supported.

        """
        for tool_dir in self.meta_files_location.iterdir():
            if tool_dir.name in self.tool_dirs:
                for tool_path in tool_dir.iterdir():
                    if (tool_path / self.meta_filename).is_file():
                        self.able_to_check[f"{self.config.prefix}{tool_path.stem}"] = tool_path
        if not self.able_to_check:
            self.logger.error(
                f"No single configuration for upstream check found."
                f" Something is wrong in path {self.meta_files_location}"
            )

    def _generate_meta_files(self, tools: [List, str]):

        meta_handler = MetaHandler(self.config, self.force_refresh)
        if not self.disable_remote_download:
            meta_handler.get_meta_files_from_gitlab(tools, self.config.branch)
            self.tool_dirs = meta_handler.tool_dirs
        else:
            self.logger.debug("Download disabled, nothing to generate.")
            self.tool_dirs = meta_handler.read_index_file(self.config.tools_repo_path / "index.yml")
        self._set_available_checkers()

    def get_versions_single_tool(
            self, tool_name: str, local_tool: ToolInfo, remote_tool: ToolInfo
    ) -> Tuple[ToolInfo, ToolInfo]:
        self._generate_meta_files(tool_name)
        tool_path = self.able_to_check.get(tool_name)
        if not tool_path:
            raise FileNotFoundError(f"Upstream check not implemented for {tool_name}.")
        if remote_tool:
            self._set_single_tool_upstream_versions(tool_path, remote_tool)
        else:
            self._set_single_tool_upstream_versions(tool_path, local_tool)

        return local_tool, remote_tool

    def _set_single_tool_upstream_versions(self, tool_path: pathlib.Path, tool: ToolInfo):

        with open(tool_path / self.meta_filename) as f:
            conf = json.load(f)
            # Expect list or single object in "upstreams" value
            for tool_info in (
                    conf.get("upstreams")
                    if isinstance(conf.get("upstreams"), List)
                    else [conf.get("upstreams")]
            ):
                provider = tool_info.get("provider").lower()
                if provider not in classmap.keys():
                    self.logger.error(
                        f"No upstream checker implemented for tool '{tool.name}' with provider '{provider}'. Check "
                        f"JSON configuration. "
                    )
                    continue
                cache_d = self._read_checker_cache(tool_path.stem, provider)
                if cache_d and not self.force_refresh:
                    ver_obj = self._handle_checker_cache_data(cache_d, tool_info)
                    if ver_obj:
                        tool.upstream_v.append(ver_obj)
                        self.logger.debug(
                            f"Using cached upstream version info for tool {tool.name:<{40}}"
                        )
                        continue

                self.logger.info(
                    f"Fetching origin version information from provider {tool_info.get('provider')}"
                    f" for tool {tool.name:<{40}}"
                )
                token_provider = tool_info.get("token_provider") or provider
                token = self.tokens.get(token_provider) if self.tokens else ""
                upstream_info = classmap.get(provider)(tool_info, token=token)
                updated = datetime.now()
                ver_obj = VersionInfo(
                    upstream_info.get_version(),
                    upstream_info,
                    {"latest"},
                    updated,
                    origin=upstream_info.origin,
                )

                self._write_checker_cache(
                    tool_path.stem,
                    provider,
                    {
                        "version": ver_obj.version,
                        "provider": provider,
                        "updated": format_time(updated),
                        "extra_info": upstream_info.extra_info,
                    },
                )
                tool.upstream_v.append(ver_obj)

    def _read_checker_cache(self, tool_name: str, provider: str) -> dict:

        path = self.config.cache_location / tool_name / f"{provider}_cache.json"
        if path.is_file():
            with open(path, "r") as f:
                try:
                    cache_obj = json.load(f)
                    return cache_obj
                except json.JSONDecodeError:
                    self.logger.error(
                        f"Failed to read checker cache of tool '{tool_name}' of provider '{provider}'"
                    )
                    return {}
        else:
            return {}

    def _handle_checker_cache_data(self, data: dict, tool_info: dict) -> Union[VersionInfo, None]:
        now = datetime.now()
        timestamp = parse_file_time(data.get("updated"))
        if now - timedelta(hours=self.config.cache_lifetime) <= timestamp <= now:
            # Use cache file if in time range
            dummy_checker = classmap.get(tool_info.get("provider").lower())(
                tool_info,
                version=data.get("version"),
                extra_info=data.get("extra_info"),
            )
            ver_obj = VersionInfo(
                data.get("version"),
                dummy_checker,
                {"latest"},
                timestamp,
                tool_info.get("origin"),
            )
            return ver_obj
        return None

    def _write_checker_cache(self, tool_name: str, provider: str, data: dict):
        path = self.config.cache_location / tool_name / f"{provider}_cache.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
            self.logger.debug(
                f"Writing checker cache of tool {tool_name} for provider {provider} into {path}"
            )

    async def check_upstream_versions(self, tools: Dict[str, ToolInfo]):
        """
        Checks for available versions in upstream
        """
        tasks = []
        self._generate_meta_files(tools)
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
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
                for _ in await asyncio.gather(*tasks):
                    pass
            else:
                self.logger.warning(
                    "No known methods to get updates for any of the local tools."
                )
        return tools

    async def list_versions_single(
            self, l_tool: ToolInfo, r_tool: ToolInfo, only_updates: bool = False
    ) -> dict:
        """
        Generates version information for single tool. Attempts to define if there are
        new versions available.
        """
        tool_info = {"name": r_tool.name if r_tool else l_tool.name, "versions": {}}
        if l_tool:
            l_latest = l_tool.get_latest()
            tool_info["versions"]["local"] = {
                "version": l_latest.version,
                "tags": list(l_latest.tags),
            }
        if r_tool:
            r_latest = r_tool.get_latest()
            tool_info["versions"]["remote"] = {
                "version": r_latest.version,
                "tags": list(r_latest.tags),
            }

        r_tool_orig = r_tool.get_origin_version()
        if not r_tool_orig.provider:
            r_tool_orig = r_tool.get_docker_origin_version()

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
            if l_tool.get_latest() == r_tool.get_latest():
                tool_info["updates"]["local"] = False
            else:
                tool_info["updates"]["local"] = True

        # Remote to upstream
        r_latest = r_tool.get_latest()
        r_up_latest = r_tool.get_latest(in_upstream=True)
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

        if only_updates:
            if tool_info["updates"]["remote"] or (
                    tool_info["updates"]["local"] if l_tool else False
            ):
                return tool_info
            else:
                return {}

        return tool_info
