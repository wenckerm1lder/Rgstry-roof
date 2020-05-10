from typing import Dict, List, Tuple
from .tool_info import ToolInfo
from .version_info import VersionInfo
from .checkers import classmap
from .gitlab_utils import GitLabAPI
from .utils import parse_file_time, format_time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pathlib
import json
from datetime import datetime, timedelta
import logging
import asyncio
import base64


class VersionMaintainer:
    """
    Class for getting possible new versions for tools in ToolRegistry
    """

    def __init__(
        self,
        tokens: dict = None,
        meta_filename: str = "meta.json",
        prefix: str = "cincan/",
        metafiles_location: str = "",
        cachefiles_location: str = "",
        disable_remote_download: bool = False,
        force_refresh: bool = False,
    ):
        self.logger = logging.getLogger("versions")
        self.tokens = tokens or {}
        self.max_workers = 30
        self.cache_lifetime = 24  # Cache validity in hours
        # prefix, mostly meaning the owner of possible Docker image
        self.prefix = prefix
        self.meta_filename = meta_filename
        # Used when storing metafiles in different place than cache
        self.metafiles_location = (
            pathlib.Path(metafiles_location)
            if metafiles_location
            else pathlib.Path.home() / ".cincan" / "version_cache"
        )
        # Path where metafiles are downloaded
        # Or version cache kept
        self.cachefiles_location = (
            pathlib.Path(cachefiles_location)
            if cachefiles_location
            else pathlib.Path.home() / ".cincan" / "version_cache"
        )

        self.disable_remote_download = disable_remote_download
        if self.disable_remote_download:
            self.logger.warning(
                "Remote download disabled for meta files - using local files and they are not updated automatically."
            )
        self.force_refresh = force_refresh
        # CinCan GitLab repository details
        self.namespace = "cincan"
        self.project = "tools"

        self.able_to_check = {}

    def _set_available_checkers(self) -> Dict:
        """
        Gets dictionary of tools, whereas upstream/origin check is supported.

        """
        for tool_path in self.metafiles_location.iterdir():
            self.able_to_check[f"{self.prefix}{tool_path.stem}"] = tool_path
        if not self.able_to_check:
            self.logger.error(
                f"No single configuration for upstream check found. Something is wrong in path {self.metafiles_location}"
            )

    def _is_old_metafile_usable(self, local_path: pathlib.Path) -> bool:

        if isinstance(local_path, pathlib.Path):
            local_path = self.cachefiles_location / local_path
        else:
            raise AttributeError("Given path is not Path object.")
        if not local_path.is_file():
            self.logger.debug(
                f"No existing metafile found for {local_path.parent.stem}"
            )
            return False
        mtime = datetime.fromtimestamp(local_path.stat().st_mtime)
        now = datetime.now()
        if now - timedelta(hours=self.cache_lifetime) <= mtime <= now:
            self.logger.debug(
                f"Using old metafile for {local_path.parent.stem} : updated in past {self.cache_lifetime} hours."
            )
            return True
        else:
            self.logger.info(
                f"Outdated metafile for {local_path.parent.stem}. Updating..."
            )
            return False

    def _fetch_write_metafile_by_path(
        self, client: GitLabAPI, path: pathlib.Path, ref: str
    ) -> pathlib.Path:

        if not self.force_refresh:
            if self._is_old_metafile_usable(path):
                return
        resp = client.get_file_by_path(str(path), ref=ref)
        file_path = None
        if resp:
            file_data = base64.b64decode(resp.get("content"))
            if str(path).count("/") > 1 or str(path).startswith("_"):
                self.logger.warning(
                    f"File {str(path)} in wrong place at GitLab repository, skipping..."
                )
                return
            file_path = self.cachefiles_location / path
            # Make subdirectory - should be tool name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(file_data)
                self.logger.info(f"Metafile generated into {file_path}")
        else:
            self.logger.info(f"No metafile for {path.parent} from GitLab")
        return file_path

    def _get_checker_meta_files_from_gitlab(
        self, tools: [List, str], branch: str = "master", prefix="cincan"
    ):

        if tools:
            # Create store location directory
            self.cachefiles_location.mkdir(parents=True, exist_ok=True)
        else:
            raise ValueError("Empty 'tools' attribute provided to metafiles fetch.")

        self.logger.info(
            f"Checking upstream information files from GitLab (https://gitlab.com/{self.namespace}/{self.project}) into path '{self.cachefiles_location}'"
        )
        gitlab_client = GitLabAPI(
            self.tokens.get("gitlab"), self.namespace, self.project
        )

        if isinstance(tools, str):
            tools = [tools]
        # tools without 'cincan' prefix
        tools = [
            (pathlib.Path(i.split("/", 1)[1]) / self.meta_filename)
            for i in tools
            if i.startswith(prefix)
        ]

        # NOTE slower at lower tool amounts but safer method
        # Get list of all files in repository
        # meta_tools contain only tools with meta files - no extra 404 later
        if len(tools) > 1:
            files = gitlab_client.get_full_tree(per_page=100, recursive=True, ref=branch)
            # Get paths of each meta file
            meta_paths = []
            for file in files:
                if file.get("name") == self.meta_filename:
                    p = pathlib.Path(file.get("path"))
                    if p in tools:
                        meta_paths.append(p)
            if not meta_paths:
                raise FileNotFoundError(
                    f"No single meta file ({self.meta_filename}) found from GitLab ({self.namespace}/{self.project})"
                )
        else:
            meta_paths = tools

        # Write and fetch each file from GitLab
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Start the load operations and mark each future with its path
            future_to_fetch = {
                executor.submit(
                    self._fetch_write_metafile_by_path, gitlab_client, path, branch
                ): path
                for path in meta_paths
            }
            for future in as_completed(future_to_fetch):
                path = future_to_fetch[future]
                try:
                    future.result()
                except Exception as exc:
                    self.logger.error(f"{path} generated an exception: {exc}")
                else:
                    pass

            self.logger.info("Required metafiles checked.")

    def generate_metafiles(self, tools: [List, str]):

        if not self.disable_remote_download:
            self._get_checker_meta_files_from_gitlab(tools)
        else:
            self.logger.debug("Download disabled, nothing to generate.")
        self._set_available_checkers()

    def get_versions_single_tool(
        self, tool_name: str, local_tool: ToolInfo, remote_tool: ToolInfo
    ) -> Tuple[ToolInfo, ToolInfo]:
        self.generate_metafiles(tool_name)
        tool_path = self.able_to_check.get(tool_name)
        if not tool_path:
            raise FileNotFoundError(f"Upstream check not implemented for {tool_name}.")
        if remote_tool:
            self._set_single_tool_upstream_versions(tool_path, remote_tool)
        else:
            self._set_single_tool_upstream_versions(tool_path, local_tool)

        return local_tool, remote_tool

    def _set_single_tool_upstream_versions(self, tool_path: str, tool: ToolInfo) -> str:

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
                        f"No upstream checker implemented for tool '{tool.name}' with provider '{provider}'. Check JSON configuration."
                    )
                    continue
                cache_d = self._read_checker_cache(tool_path.stem, provider)
                if cache_d and not self.force_refresh:
                    ver_obj = self._handle_checker_cache_data(cache_d, tool_info)
                    if ver_obj:
                        tool.upstream_v.append(ver_obj)
                        self.logger.debug(
                            f"Using cached upstream version info for tool {tool.name:<{40}}\r\r"
                        )
                        continue

                self.logger.info(
                    f"Fetching origin version information for tool {tool.name:<{40}}\r\r"
                )
                token_provider = tool_info.get("token_provider") or provider
                token = self.tokens.get(token_provider) if self.tokens else ""
                upstream_info = classmap.get(provider)(tool_info, token=token)
                updated = datetime.now()
                ver_obj = VersionInfo(
                    upstream_info.get_version(),
                    upstream_info,
                    set({"latest"}),
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

        path = self.cachefiles_location / tool_name / f"{provider}_cache.json"
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

    def _handle_checker_cache_data(self, data: dict, tool_info: dict) -> VersionInfo:
        now = datetime.now()
        timestamp = parse_file_time(data.get("updated"))
        if now - timedelta(hours=self.cache_lifetime) <= timestamp <= now:
            # Use cache file if in time range
            dummy_checker = classmap.get(tool_info.get("provider").lower())(
                tool_info,
                version=data.get("version"),
                extra_info=data.get("extra_info"),
            )
            ver_obj = VersionInfo(
                data.get("version"),
                dummy_checker,
                set({"latest"}),
                timestamp,
                tool_info.get("origin"),
            )
            return ver_obj
        return None

    def _write_checker_cache(self, tool_name: str, provider: str, data: dict):
        path = self.cachefiles_location / tool_name / f"{provider}_cache.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
            self.logger.debug(
                f"Writing checker cache of tool {tool_name} for provider {provider} into {path}"
            )

    async def _check_upstream_versions(self, tools: List):
        """
        Checks for available versions in upstream
        """
        tasks = []
        self.generate_metafiles(tools)
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

    async def _list_versions_single(
        self, l_tool: ToolInfo, r_tool: ToolInfo, only_updates: bool = False
    ) -> dict:
        """
        Generates version information for single tool. Attempts to define if there are
        new versions available.
        """
        tool_info = {}
        tool_info["name"] = r_tool.name if r_tool else l_tool.name
        tool_info["versions"] = {}
        if l_tool:
            l_latest = l_tool.getLatest()
            tool_info["versions"]["local"] = {
                "version": l_latest.version,
                "tags": list(l_latest.tags),
            }
        if r_tool:
            r_latest = r_tool.getLatest()
            tool_info["versions"]["remote"] = {
                "version": r_latest.version,
                "tags": list(r_latest.tags),
            }

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

        if only_updates:
            if tool_info["updates"]["remote"] or (
                tool_info["updates"]["local"] if l_tool else False
            ):
                return tool_info
            else:
                return {}

        return tool_info
