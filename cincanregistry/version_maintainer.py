import asyncio
import json
import logging
import queue
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Tuple, List

from cincanregistry.models.tool_info import ToolInfo
from cincanregistry.models.version_info import VersionInfo, VersionType
from .checkers import classmap, UpstreamChecker, NO_VERSION
from .configuration import Configuration
from .database import ToolDatabase
from .utils import read_index_file

UPSTREAM_TAG = "upstream"


class VersionMaintainer:
    """
    Class for getting possible new versions for tools in ToolRegistry
    """

    def __init__(
            self,
            configuration: Configuration,
            db: ToolDatabase,
            force_refresh: bool = False,
    ):
        self.config = configuration
        self.db = db
        self.logger = logging.getLogger("versions")
        self.tokens = self.config.tokens
        # Use local 'tools' path if provided instead of database
        self.meta_files_location = self.config.tools_repo_path
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
        self.tool_dirs = []
        self.cache_write_queue = queue.Queue()

    def _get_upstreams_local_metafile(self, tool_name: str) -> List[Dict]:
        """Read local metafile from cloned https://gitlab.com/CinCan/tools """
        tool_locations = read_index_file(self.meta_files_location / self.config.index_file)
        for t in tool_locations:
            # Tool should be only in one place
            meta_path = self.meta_files_location / t / tool_name / self.meta_filename
            if meta_path.is_file():
                with meta_path.open("r") as f:
                    return json.load(f).get("upstreams")

    def _set_single_tool_upstream_versions(self, tool: ToolInfo, in_thread=False):
        """Update upstream information of given tool"""

        if in_thread:
            # New db connection inside thread
            db = ToolDatabase(self.config)
        else:
            db = self.db

        if not self.meta_files_location:
            # Expect list or single object in "upstreams" value
            upstreams = db.get_meta_information(tool.name)
        else:
            # If path for local files is provided, use them instead of DB
            upstreams = self._get_upstreams_local_metafile(tool.name)
        if not upstreams:
            self.logger.debug(f"Upstream check not implemented for tool {tool.name}")
            return
        for upstream_info in upstreams:
            provider = upstream_info.get("provider").lower()
            if provider not in classmap.keys():
                self.logger.error(
                    f"No upstream checker implemented for tool '{tool.name}' with provider '{provider}'. Check "
                    f"JSON configuration. "
                )
                continue
            cache_d = self._read_checker_cache(tool.name, provider, db)
            token_provider = upstream_info.get("token_provider") or provider
            token = self.tokens.get(token_provider) if self.tokens else ""
            # Don't use cached version if was not found last time - instead try to fetch again
            if cache_d and not self.force_refresh and cache_d.version != NO_VERSION:
                now = datetime.now()
                if now - timedelta(hours=self.config.cache_lifetime) <= cache_d.updated <= now:
                    cache_d.source = classmap.get(provider)(upstream_info, token=token)
                    cache_d.updated = now
                    tool.versions.append(cache_d)
                    self.logger.debug(
                        f"Using cached upstream version info for tool {tool.name:<{40}}"
                    )
                    continue

            self.logger.info(
                f"Fetching origin version information from provider {upstream_info.get('provider')}"
                f" for tool {tool.name:<{40}}"
            )
            upstream_info = classmap.get(provider)(upstream_info, token=token)
            updated = datetime.now()
            ver_obj = VersionInfo(
                upstream_info.get_version(),
                VersionType.UPSTREAM,
                upstream_info,
                {UPSTREAM_TAG},
                updated,
                origin=upstream_info.origin,
            )
            self.cache_write_queue.put((tool, ver_obj))
            tool.versions.append(ver_obj)

    def _read_checker_cache(self, tool_name: str, provider: str, db: ToolDatabase = None) -> VersionInfo:
        """Read version data of tool by provider from db"""
        if not db:
            db = self.db
        version = db.get_versions_by_tool(tool_name, [VersionType.UPSTREAM], provider=provider.lower(), latest=True)
        return version

    def _write_upstream_version_data(self, tool: ToolInfo, data: VersionInfo, as_transaction: bool = True):
        """Cache data of single provider of single tool"""
        if as_transaction:
            with self.db.transaction():
                self.db.insert_version_info(tool, data)
        else:
            self.db.insert_version_info(tool, data)

    def _write_cache_queue_into_db(self):
        """Unable to write from multiple threads, write from here at once"""
        # Rollback if any item from queue fails
        with self.db.transaction():
            while not self.cache_write_queue.empty():
                tool, version = self.cache_write_queue.get()
                self._write_upstream_version_data(tool, version, False)

    def get_versions_single_tool(
            self, tool_name: str, local_tool: ToolInfo, remote_tool: ToolInfo
    ) -> Tuple[ToolInfo, ToolInfo]:

        if remote_tool:
            self._set_single_tool_upstream_versions(remote_tool)
        else:
            self._set_single_tool_upstream_versions(local_tool)
        # Write changes of upstream versions into db at once
        self._write_cache_queue_into_db()

        return local_tool, remote_tool

    async def check_upstream_versions(self, tools: Dict[str, ToolInfo]):
        """
        Checks for available versions in upstream
        """
        tasks = []
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            for t in tools:
                # Basename is needed - version check works with different registries
                tool = tools.get(t)
                loop = asyncio.get_event_loop()
                tasks.append(
                    loop.run_in_executor(
                        executor,
                        self._set_single_tool_upstream_versions,
                        *(tool, True),
                    )
                )
            if tasks:
                for _ in await asyncio.gather(*tasks):
                    pass
                # Sqlite is not good when multi-thread writing - use queue
                self._write_cache_queue_into_db()
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
            r_latest = r_tool.get_latest(in_remote=True)
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
            if (r_tool_orig.origin or r_tool_orig.docker_origin) and isinstance(r_tool_orig.source, UpstreamChecker)
            else {"provider": r_tool_orig.source}
        )

        tool_info["versions"]["other"] = [
            {
                "version": v.version,
                "details": dict(v.source)
                if not isinstance(v.source, str)
                else {"provider": v.source},
            }
            for v in r_tool.versions
            if not v.origin and v.source and v.version_type == VersionType.UPSTREAM
        ]
        tool_info["updates"] = {}

        # Compare all versions, if there are updates available #

        # Compare local to remote at first
        if l_tool:
            if l_tool.get_latest() == r_tool.get_latest(in_remote=True):
                tool_info["updates"]["local"] = False
            else:
                tool_info["updates"]["local"] = True

        # Remote to upstream
        r_latest = r_tool.get_latest(in_remote=True)
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
