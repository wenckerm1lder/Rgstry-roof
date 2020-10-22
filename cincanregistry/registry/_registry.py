import re
import asyncio
import json
import logging
import pathlib
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Tuple, Union, List
from abc import ABCMeta, abstractmethod
import docker
import docker.errors
import requests
from datetime import datetime, timedelta
from cincanregistry import ToolInfo, ToolInfoEncoder, VersionInfo, VersionMaintainer
from cincanregistry.utils import parse_file_time, split_tool_tag
from cincanregistry.configuration import Configuration

REMOTE_REGISTRY = "Dockerhub"
LOCAL_REGISTRY = "Docker Server"


class ToolRegistry(metaclass=ABCMeta):
    """A tool registry
    Implements client for Docker Registry HTTP V2 API
    https://docs.docker.com/registry/spec/api/

    Gives additional abstract methods for specific registries to list
    images etc. which might not be supported by normal API.

    """
    VER_UNDEFINED = "undefined"
    CACHE_VERSION_VAR = "__cache_version"

    def __init__(
            self,
            config_path: str = "",
            tools_repo_path: str = "",
            version_var="TOOL_VERSION",
    ):
        self.logger: logging.Logger = logging.getLogger("registry")
        self.client: docker.DockerClient = docker.from_env()
        self.schema_version: str = "v2"
        self.registry_name: str = ""
        # Root of Docker Registry HTTP API V2
        self.registry_root: str = ""
        self.registry_service: str = ""
        self.auth_digest_type: str = "Bearer"
        self.auth_url: str = ""
        # Root of custom API of registry provider for extra functionality
        self.custom_api_root: str = ""
        self.version_var: str = version_var
        self.config: Configuration = Configuration(config_path, tools_repo_path)
        self.max_workers: int = self.config.max_workers
        self.tool_cache: pathlib.Path = self.config.tool_cache
        self.tool_cache_version: str = self.config.tool_cache_version
        self.tools_repo_path: pathlib.Path = self.config.tools_repo_path

        # Using single Requests.Session instance here
        self.session: requests.Session = requests.Session()
        # Adapter allows more simultaneous connections
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=self.max_workers)
        self.session.mount("https://", adapter)

    def __del__(self):
        self.session.close()

    def _is_docker_running(self):
        """
        Check if Docker Daemon is running
        """
        try:
            self.client.ping()
            return True
        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to connect to Docker Server. Is it running?")
            self.logger.error("Not able to list or use local tools.")
            return False

    def _docker_registry_api_error(
            self, r: requests.Response, custom_error_msg: str = ""
    ):
        """
        Logs error response caused by Docker Registry HTTP API V2
        """
        if custom_error_msg:
            self.logger.error(f"{custom_error_msg}")
        for error in r.json().get("errors"):
            self.logger.debug(
                f"{error.get('code')}: {error.get('message')} Additional details: {error.get('detail')}"
            )

    def _set_auth_and_service_location(self):
        """
        Set registry auth endpoint and actual service location from root url
        Acquired from the www-authenticate header with HEAD (or GET) against v2 api
        """

        init_req = self.session.head(f"{self.registry_root}/{self.schema_version}/")
        www_auth = init_req.headers.get("www-authenticate", "")
        if not www_auth:
            raise ValueError("No WWW-Authenticate header - unable to get auth details.")
        # Parse key value pairs into dict
        reg = re.compile(r'(\w+)[:=][\s"]?([^",]+)"?')
        parsed_www = dict(reg.findall(www_auth))
        self.registry_service = parsed_www.get("service", "")
        self.auth_url = parsed_www.get("realm", "")
        try:
            self.auth_digest_type = www_auth.split(" ", 1)[0]
        except IndexError():
            self.logger.warning(f"Unable to get token digest type from {self.registry_root} , using default.")

    def _get_registry_service_token(self, repo: str) -> str:
        """
        Gets Bearer token with 'pull' scope for single repository
        in Docker Registry HTTP API V2 by default.
        """
        params = {
            "service": self.registry_service,
            "scope": f"repository:{repo}:pull",
        }
        token_req = self.session.get(self.auth_url, params=params)
        if token_req.status_code != 200:
            self._docker_registry_api_error(
                token_req, f"Error when getting token for repository {repo}"
            )
            return ""
        else:
            return token_req.json().get("token", "")

    def _get_version_from_containerconfig_env(self, attrs: dict) -> str:
        """
        Parse version information ENV from local image attributes
        """
        environment = attrs.get("Config").get("Env")
        for var in environment:
            if "".join(var).split("=")[0] == self.version_var:
                version = "".join(var).split("=")[1]
                return version
        return ""

    def get_version_by_image_id(self, image_id: str) -> str:
        """Get version of local image by ID"""
        if not self._is_docker_running():
            return ""
        image = self.client.images.get(image_id)
        version = self._get_version_from_containerconfig_env(image.attrs)
        return version

    def _get_version_from_manifest(
            self, manifest: dict,
    ):
        """
        Parses value from defined variable from container's environment variables.
        In this case, defined variable is expected to contain version information.

        Applies for old V1 manifest.
        """

        v1_comp_string = manifest.get("history", [{}])[0].get("v1Compatibility")
        if v1_comp_string is None:
            return {}
        v1_comp = json.loads(v1_comp_string)
        # Get time and convert to Datetime object
        updated = parse_file_time(v1_comp.get("created"))
        version = ""
        try:
            for i in v1_comp.get("config").get("Env"):
                if "".join(i).split("=")[0] == self.version_var:
                    version = "".join(i).split("=")[1]
                    break
        except IndexError as e:
            self.logger.warning(
                f"No version information for tool {manifest.get('name')}: {e}"
            )
        return version, updated

    def fetch_manifest(
            self, name: str, tag: str
    ) -> Dict[str, Any]:
        """Fetch docker image manifest information by tag"""

        # Get authentication token for tool with pull scope
        token = self._get_registry_service_token(name)

        manifest_req = self.session.get(
            f"{self.registry_root}/{self.schema_version}/{name}/manifests/{tag}",
            headers={
                "Authorization": f"{self.auth_digest_type} {token}",
                "Accept": "application/vnd.docker.distribution.manifest.v1+json",
            },
        )
        if manifest_req.status_code != 200:
            self._docker_registry_api_error(
                manifest_req,
                f"Error when getting manifest for tool {name}. Code {manifest_req.status_code}",
            )
            return {}
        return manifest_req.json()

    async def get_local_remote_tools(self, defined_tag: str = "") -> Tuple[Dict, Dict]:
        """
        Get remote and local tools in parallel to increase performance
        """
        tasks = [
            self.list_tools_local_images(defined_tag),
            self.list_tools_registry(defined_tag),
        ]
        local_tools, remote_tools = await asyncio.ensure_future(asyncio.gather(*tasks))
        return local_tools, remote_tools

    def list_tools(self, defined_tag: str = "", merge=True) -> Dict[str, ToolInfo]:
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
                    for ver in r_tool.versions:
                        if defined_tag in ver.tags:
                            r_version = ver.version
                            # Add size based on remote version
                            # compressed
                            size = ver.size
                            break
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
                r_obj = remote_tools.get(i).get_latest() if remote_tools.get(i) else None
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

    def create_local_tool_info_by_name(self, name: str) -> Union[ToolInfo, None]:
        """Find local images by name, return ToolInfo object with version list"""
        if not self._is_docker_running():
            return None
        images = self.client.images.list(name, filters={"dangling": False})
        if not images:
            return None
        source = "local"
        name, tag = split_tool_tag(name)
        tool = ToolInfo(name, datetime.now(), source)
        images.sort(key=lambda x: parse_file_time(x.attrs["Created"]), reverse=True)
        versions = []
        for i in images:
            updated = parse_file_time(i.attrs["Created"])
            version = self._get_version_from_containerconfig_env(i.attrs)
            if not version:
                version = self.VER_UNDEFINED
            tags = set(i.tags)
            size = i.attrs.get("Size")
            if not versions:
                versions.append(VersionInfo(version, source, tags, updated, size=size))
                continue
            for v in versions:
                if v == version:
                    v.tags.union(tags)
                    break
                else:
                    versions.append(
                        VersionInfo(version, source, tags, updated, size=size)
                    )
        tool.versions = versions
        return tool

    async def list_tools_local_images(
            self,
            defined_tag: str = "",
            prefix: str = "cincan/",
            default_ver: str = VER_UNDEFINED,
    ) -> Dict[str, ToolInfo]:
        """
        List tools from the locally available docker images
        Only tools with starts with 'prefix' are listed.
        Additionally, if tag is defined, tool must have this tag
        before it is listed.
        """
        if not self._is_docker_running():
            return {}
        images = self.client.images.list(filters={"dangling": False})
        # images oldest first (tags are listed in proper order)
        images.sort(key=lambda x: parse_file_time(x.attrs["Created"]), reverse=True)
        ret = {}
        for i in images:
            if len(i.tags) == 0:
                continue  # not sure what these are...
            updated = parse_file_time(i.attrs["Created"])
            for t in i.tags:
                version = default_ver
                existing_ver = False
                stripped_tags = [
                    split_tool_tag(tag)[1] if tag.startswith(prefix) else tag
                    for tag in i.tags
                ]
                name, tag = split_tool_tag(t)
                if name.startswith(prefix):
                    if not defined_tag or tag == defined_tag:
                        version = self._get_version_from_containerconfig_env(i.attrs)
                        if name in ret:
                            for j, v in enumerate(ret[name].versions):
                                if v.version == version:
                                    existing_ver = True
                                    self.logger.debug(
                                        f"same version found for tool {name} with version {version} as tag {tag} "
                                    )
                                    ret[name].versions[j].tags.union(set(stripped_tags))
                                    break
                            if not existing_ver:
                                self.logger.debug(
                                    f"Appending new version {version} to existing entry {name} with tag {tag}."
                                )
                                ret[name].versions.append(
                                    VersionInfo(
                                        version,
                                        LOCAL_REGISTRY,
                                        set(stripped_tags),
                                        updated,
                                        size=i.attrs.get("Size"),
                                    )
                                )
                        else:
                            ver_info = VersionInfo(
                                version,
                                LOCAL_REGISTRY,
                                set(stripped_tags),
                                updated,
                                size=i.attrs.get("Size"),
                            )
                            ret[name] = ToolInfo(
                                name, updated, "local", versions=[ver_info]
                            )
                            self.logger.debug(
                                f"Added local tool {name} based on tag {t} with version {version}"
                            )
                            continue
                    else:
                        continue
        return ret

    def update_cache_by_tool(self, tool: ToolInfo):
        self.tool_cache.parent.mkdir(parents=True, exist_ok=True)
        tools = {}
        if self.tool_cache.is_file():
            with self.tool_cache.open("r") as f:
                tools = json.load(f)
                if not tools.get(self.CACHE_VERSION_VAR) == self.tool_cache_version:
                    tools = {}
        with self.tool_cache.open("w") as f:
            tools[self.CACHE_VERSION_VAR] = self.tool_cache_version
            tools[tool.name] = dict(tool)
            self.logger.debug(f"Updating tool cache for tool {tool.name}")
            json.dump(tools, f, cls=ToolInfoEncoder)

    def read_tool_cache(
            self, tool_name: str = ""
    ) -> Union[Dict[str, ToolInfo], ToolInfo]:
        """
        Read the local tool cache file
        Returns all as dictionary, or single tool as ToolInfo object
        """
        # json.decoder.JSONDecodeError
        if not self.tool_cache.exists():
            return {}
        r = {}
        with self.tool_cache.open("r") as f:
            try:
                root_json = json.load(f)
            except json.decoder.JSONDecodeError:
                self.logger.warning(
                    f"Something wrong with '{self.tool_cache.stem}' cache, deleting it ..."
                )
                self.tool_cache.unlink()
                return {}
            c_ver = root_json.get(self.CACHE_VERSION_VAR, "")
            if not c_ver == self.tool_cache_version:
                self.tool_cache.unlink()
                return {}
            else:
                del root_json[self.CACHE_VERSION_VAR]
            try:
                if tool_name:
                    d = root_json.get(tool_name, {})
                    return ToolInfo.from_dict(d) if d else {}
                for name, j in root_json.items():
                    r[name] = ToolInfo.from_dict(j)
            # If cache is modified to contain extra variables
            except TypeError:
                self.tool_cache.unlink()
                return {}
        return r

    async def list_versions(
            self,
            tool: str = "",
            to_json: bool = False,
            only_updates: bool = False,
            force_refresh: bool = False,
    ):
        maintainer = VersionMaintainer(
            self.config,
            force_refresh=force_refresh,
        )
        versions = {}
        if tool:
            l_tool = self.create_local_tool_info_by_name(tool)
            r_tool = self.read_tool_cache(tool)
            now = datetime.now()
            if not r_tool:
                r_tool = ToolInfo(tool, datetime.min, "remote")
            if not r_tool.updated or not (
                    now - timedelta(hours=24) <= r_tool.updated <= now
            ):
                with requests.Session() as s:
                    self.fetch_tags(s, r_tool, update_cache=True)
            if l_tool or (r_tool and not r_tool.updated == datetime.min):
                l_tool, r_tool = maintainer.get_versions_single_tool(
                    tool, l_tool, r_tool
                )
                versions = await maintainer.list_versions_single(
                    l_tool, r_tool, only_updates
                )
            else:
                raise FileNotFoundError(
                    f"Given tool {tool} not found locally or remotely."
                )
        else:
            remote_tools = await self.list_tools_registry()
            # Remote tools, with included upstream version information
            remote_tools_with_origin_version = await maintainer.check_upstream_versions(
                remote_tools
            )
            # Local tools, without checking
            local_tools = await self.list_tools_local_images()
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

    @abstractmethod
    def fetch_tags(self, tool: ToolInfo, update_cache: bool = False):
        pass

    @abstractmethod
    async def list_tools_registry(self, defined_tag: str = "") -> Dict[str, ToolInfo]:
        pass
