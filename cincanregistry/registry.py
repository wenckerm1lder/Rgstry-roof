import asyncio
import json
import logging
import pathlib
import timeit
import base64
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Tuple, Union, List
import docker
import docker.errors
import requests
from datetime import datetime, timedelta
from . import ToolInfo, ToolInfoEncoder, VersionInfo, VersionMaintainer
from .utils import parse_file_time, split_tool_tag
from .configuration import Configuration

VER_UNDEFINED = "undefined"
REMOTE_REGISTRY = "Dockerhub"
LOCAL_REGISTRY = "Docker Server"
CACHE_VERSION_VAR = "__cache_version"


class ToolRegistry:
    """A tool registry"""

    def __init__(
            self,
            config_path: str = "",
            tools_repo_path: str = "",
            version_var="TOOL_VERSION",
    ):
        self.logger = logging.getLogger("registry")
        self.client = docker.from_env()

        self.schema_version = "v2"
        self.hub_url = f"https://hub.docker.com/{self.schema_version}"
        self.auth_url = "https://auth.docker.io/token"
        self.registry_service = "registry.docker.io"
        self.registry_host = "registry.hub.docker.com"
        self.registry_url = f"https://{self.registry_host}/{self.schema_version}"
        self.max_page_size = 1000
        self.version_var = version_var
        self.config = Configuration(config_path, tools_repo_path)
        self.max_workers = self.config.max_workers
        self.tool_cache = self.config.tool_cache
        self.tool_cache_version = self.config.tool_cache_version
        self.tools_repo_path = self.config.tools_repo_path

    def _is_docker_running(self):
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

    def _get_registry_service_token(self, session: requests.Session, repo: str) -> str:
        """
        Gets Bearer token with 'pull' scope for single repository
        in Docker Registry by default.
        """
        params = {
            "service": self.registry_service,
            "scope": f"repository:{repo}:pull",
        }
        token_req = session.get(self.auth_url, params=params)
        if token_req.status_code != 200:
            self._docker_registry_api_error(
                token_req, f"Error when getting token for repository {repo}"
            )
            return ""
        else:
            return token_req.json().get("token", "")

    def _get_hub_session_cookies(self, s: requests.Session):
        """
        Gets JWT and CSRF token for making authorized requests for Docker Hub
        Updates request Session object with valid header

        It seems Docker Hub is using cookie-to-header pattern as
        extra CSRF protection, header named as 'X-CSRFToken'
        """

        login_uri = self.hub_url + "/users/login/"
        config = docker.utils.config.load_general_config()
        auths = (
            next(iter(config.get("auths").values())) if config.get("auths") else None
        )
        if auths:
            username, password = (
                base64.b64decode(auths.get("auth")).decode("utf-8").split(":", 1)
            )
        else:
            raise PermissionError(
                "Unable to find credentials. Please use 'docker login' to log in."
            )
        data = {"username": username, "password": password}
        headers = {
            "Content-Type": "application/json",  # redundant because json as data parameter
        }
        resp = s.post(login_uri, json=data, headers=headers)
        if resp.status_code == 200:
            s.headers.update({"X-CSRFToken": s.cookies.get("csrftoken")})
        else:
            raise PermissionError(f"Failed to fetch JWT and CSRF Token: {resp.content}")

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
            self, name: str, tag: str, session: requests.Session = None
    ) -> Dict[str, Any]:
        """Fetch docker image manifest information by tag"""
        if not session:
            session = requests.Session()
        # Get authentication token for tool with pull scope
        token = self._get_registry_service_token(session, name)

        manifest_req = session.get(
            self.registry_url + "/" + name + "/manifests/" + tag,
            headers={
                "Authorization": ("Bearer " + token),
                "Accept": "application/vnd.docker.distribution.manifest.list.v2+json",
            },
        )
        if manifest_req.status_code != 200:
            self._docker_registry_api_error(
                manifest_req,
                f"Error when getting manifest for tool {name}. Code {manifest_req.status_code}",
            )
            return {}
        return manifest_req.json()

        # curl -s "https://registry.hub.docker.com/v2/repositories/cincan/"
        # curl https://hub.docker.com/v2/repositories/cincan/tshark/tags
        # curl - sSL "https://auth.docker.io/token?service=registry.docker.io&scope=repository:raulik/test-test-tool:pull" | jq - r.token > bearer - token
        # curl - s H "Authorization: Bearer `cat bearer-token`" "https://registry.hub.docker.com/v2/raulik/test-test-tool/manifests/latest" | python - m json.tool

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
                version = VER_UNDEFINED
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

    def fetch_tags(
            self, session: requests.Session, tool: ToolInfo, update_cache: bool = False
    ):
        """Fetch remote data to update a tool info"""

        available_versions: List[VersionInfo] = []
        self.logger.info("fetch %s...", tool.name)
        tool_name, tool_tag = split_tool_tag(tool.name)
        params = {"page_size": self.max_page_size}
        tags_req = session.get(
            f"{self.hub_url}/repositories/{tool_name}/tags",
            params=params,
            headers={
                "Host": self.registry_host
            },
        )
        if tags_req.status_code != 200:
            self.logger.error(
                f"Error when getting tags for tool {tool_name}: {tags_req.content}"
            )
            return
        if tags_req.json().get("count") > self.max_page_size:
            self.logger.warning(
                f"More tags ( > {self.max_page_size}) than able to list for tool {tool_name}."
            )
        tags = tags_req.json()
        # sort tags by update time
        tags_sorted = sorted(
            tags.get("results", []),
            key=lambda x: parse_file_time(x["last_updated"]),
            reverse=True,
        )
        tag_names = list(map(lambda x: x["name"], tags_sorted))
        first_run = True
        if tag_names:
            for t in tags_sorted:
                manifest = self.fetch_manifest(tool_name, t.get("name"), session=session)
                if first_run:
                    manifest_latest = manifest
                    first_run = False
                if manifest:
                    version, updated = self._get_version_from_manifest(manifest)
                    if not version:
                        version = VER_UNDEFINED
                    match = [v for v in available_versions if version == v.version]
                    if match:
                        next(iter(match)).tags.add(t.get("name"))
                    else:
                        ver_info = VersionInfo(
                            version,
                            REMOTE_REGISTRY,
                            {t.get("name")},
                            updated,
                            size=t.get("full_size"),
                        )
                        available_versions.append(ver_info)
        else:
            self.logger.error(f"No tags found for tool {tool_name} for unknown reason.")
            return
        tool.versions = available_versions
        tool.updated = datetime.now()
        if update_cache:
            self.update_cache_by_tool(tool)

    async def list_tools_registry(self, defined_tag: str = "") -> Dict[str, ToolInfo]:
        """List tools from registry with help of local cache"""
        get_fetch_start = timeit.default_timer()
        fresh_resp = None
        with requests.Session() as session:
            adapter = requests.adapters.HTTPAdapter(pool_maxsize=self.max_workers)
            session.mount("https://", adapter)
            # Get fresh list of tools from remote registry
            try:
                params = {"page_size": 1000}
                fresh_resp = session.get(
                    self.registry_url + "/repositories/cincan/", params=params
                )
            except requests.ConnectionError as e:
                self.logger.warning(e)
            if fresh_resp and fresh_resp.status_code != 200:
                self._docker_registry_api_error(
                    fresh_resp,
                    "Error getting list of remote tools, code: {}".format(
                        fresh_resp.status_code
                    ),
                )
            elif fresh_resp:
                # get a images JSON, form new tool list
                fresh_json = fresh_resp.json()
                # print(fresh_json)
                tool_list = {}
                for t in fresh_json["results"]:
                    # pprint(t)
                    # if defined_tag:
                    #     # name = f"{t['user']}/{t['name']}:{defined_tag}"
                    #     name = f"{t['user']}/{t['name']}"
                    # else:
                    name = f"{t['user']}/{t['name']}"
                    tool_list[name] = ToolInfo(
                        name,
                        parse_file_time(t["last_updated"]),
                        "remote",
                        description=t.get("description", ""),
                    )
                # update tool info, when required
                old_tools = self.read_tool_cache()
                updated = 0
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    loop = asyncio.get_event_loop()
                    tasks = []
                    for t in tool_list.values():
                        # print(t.name)
                        # if t.name == "cincan/radare2:latest-stable":
                        if (
                                t.name not in old_tools
                                or t.updated > old_tools[t.name].updated
                        ):
                            tasks.append(
                                loop.run_in_executor(
                                    executor, self.fetch_tags, *(session, t)
                                )
                            )
                            updated += 1
                        else:
                            tool_list[t.name] = old_tools[t.name]
                            self.logger.debug("no updates for %s", t.name)
                    for _ in await asyncio.gather(*tasks):
                        pass

                # save the tool list
                if updated > 0:
                    self.tool_cache.parent.mkdir(parents=True, exist_ok=True)
                    with self.tool_cache.open("w") as f:
                        self.logger.debug("saving tool cache %s", self.tool_cache)
                        tool_list[CACHE_VERSION_VAR] = self.tool_cache_version
                        json.dump(tool_list, f, cls=ToolInfoEncoder)
            # read saved tools and return
            self.logger.debug(
                f"Remote update time: {timeit.default_timer() - get_fetch_start} s"
            )
            return self.read_tool_cache()

    def update_cache_by_tool(self, tool: ToolInfo):
        self.tool_cache.parent.mkdir(parents=True, exist_ok=True)
        tools = {}
        if self.tool_cache.is_file():
            with self.tool_cache.open("r") as f:
                tools = json.load(f)
                if not tools.get(CACHE_VERSION_VAR) == self.tool_cache_version:
                    tools = {}
        with self.tool_cache.open("w") as f:
            tools[CACHE_VERSION_VAR] = self.tool_cache_version
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
            c_ver = root_json.get(CACHE_VERSION_VAR, "")
            if not c_ver == self.tool_cache_version:
                self.tool_cache.unlink()
                return {}
            else:
                del root_json[CACHE_VERSION_VAR]
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
