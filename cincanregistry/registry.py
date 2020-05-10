import asyncio
import base64
import json
import logging
import pathlib
import sys
import timeit
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, Tuple
from urllib.parse import quote_plus

import docker
import docker.errors
import requests

from . import ToolInfo, ToolInfoEncoder, VersionInfo, VersionMaintainer
from .utils import format_time, parse_file_time, split_tool_tag

VER_UNDEFINED = "undefined"
REMOTE_REGISTRY = "Dockerhub"
LOCAL_REGISTRY = "Docker Server"


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
        self.max_workers = 30
        self.max_page_size = 1000
        self.version_var = version_var
        self.conf_filepath = (
            pathlib.Path(config_path)
            if config_path
            else pathlib.Path.home() / ".cincan/registry.json"
        )
        try:
            with open(self.conf_filepath) as f:
                self.configuration = json.load(f)
        except IOError:
            self.logger.warning(
                f"No configuration file found for registry in location: {self.conf_filepath}"
            )
            self.configuration = {}
        self.tool_cache = (
            pathlib.Path(self.configuration.get("tools_cache_path"))
            if self.configuration.get("tools_cache_path")
            else pathlib.Path.home() / ".cincan" / "tools.json"
        )
        self.tools_repo_path = (
            pathlib.Path(tools_repo_path) if tools_repo_path else None
        ) or (
            pathlib.Path(self.configuration.get("tools_repo_path"))
            if self.configuration.get("tools_repo_path")
            else ""
        )

    def _is_docker_running(self):
        try:
            self.client.ping()
            return True
        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to connect to Docker Server. Is it running?")
            self.logger.error("Not able to list local tools.")
            return False

    def _docker_registry_API_error(
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

    def _get_service_token(self, session: requests.Session, repo: str) -> str:
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
            self._docker_registry_API_error(
                token_req, f"Error when getting token for repository {repo}"
            )
            return ""
        else:
            return token_req.json().get("token", "")

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
        updated = v1_comp.get("created")
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
                    local_tools.get(i).getLatest().version if local_tools.get(i) else ""
                )
                r_obj = remote_tools.get(i).getLatest() if remote_tools.get(i) else None
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

    def _get_version_from_containerconfig_env(self, attrs: dict) -> str:
        """
        Parse version informatioon ENV from local image attributes
        """
        environment = attrs.get("ContainerConfig").get("Env")
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
            # print(i.attrs.get("ContainerConfig").get("Env"))
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

    def fetch_tags(self, session: requests.Session, tool: ToolInfo) -> Dict[str, Any]:
        """Fetch remote data to update a tool info"""
        available_versions = []

        self.logger.info("fetch %s...", tool.name)

        tool_name, tool_tag = split_tool_tag(tool.name)
        params = {"page_size": self.max_page_size}
        tags_req = session.get(
            f"{self.hub_url}/repositories/{tool_name}/tags",
            params=params,
            headers={
                "Host": self.registry_host
                # "Authorization": ("Bearer " + token),
                # 'Accept': 'application/vnd.docker.distribution.manifest.v2+json',
            },
        )
        if tags_req.status_code != 200:
            self._docker_registry_API_error(
                tags_req, f"Error getting tags for tool {tool_name}"
            )
            return {}
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
        manifest_latest = {}
        first_run = True
        if tool.name.count(":") == 0 and tag_names:
            for t in tags_sorted:
                manifest = self.fetch_manifest(session, tool_name, t.get("name"))
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
            manifest = self.fetch_manifest(session, tool_name, tool_tag)
            if manifest:
                manifest_latest = manifest
                version, updated = self._get_version_from_manifest(manifest)
                available_versions.append(
                    VersionInfo(
                        version,
                        REMOTE_REGISTRY,
                        {t.get("name")},
                        updated,
                        size=t.get("full_size"),
                    )
                )
            else:
                return {}

        manifest_latest["all_tags"] = tags  # adding tags to manifest data
        manifest_latest["sorted_tags"] = tag_names
        tool.versions = available_versions
        return manifest_latest

    def fetch_manifest(
        self, session: requests.Session, name: str, tag: str
    ) -> Dict[str, Any]:
        """Fetch docker image manifest information by tag"""

        # Get authentication token for tool with pull scope
        token = self._get_service_token(session, name)

        manifest_req = session.get(
            self.registry_url + "/" + name + "/manifests/" + tag,
            headers={
                "Authorization": ("Bearer " + token),
                # 'Accept': 'application/vnd.docker.distribution.manifest.v2+json',
            },
        )
        if manifest_req.status_code != 200:
            self._docker_registry_API_error(
                manifest_req,
                f"Error when getting manifest for tool {name}. Code {manifest_req.status_code}",
            )
            return {}
        return manifest_req.json()

        # curl -s "https://registry.hub.docker.com/v2/repositories/cincan/"
        # curl https://hub.docker.com/v2/repositories/cincan/tshark/tags
        # curl - sSL "https://auth.docker.io/token?service=registry.docker.io&scope=repository:raulik/test-test-tool:pull" | jq - r.token > bearer - token
        # curl - s H "Authorization: Bearer `cat bearer-token`" "https://registry.hub.docker.com/v2/raulik/test-test-tool/manifests/latest" | python - m json.tool

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
                self._docker_registry_API_error(
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
                    for response in await asyncio.gather(*tasks):
                        pass

                # save the tool list
                if updated > 0:
                    self.tool_cache.parent.mkdir(parents=True, exist_ok=True)
                    with self.tool_cache.open("w") as f:
                        self.logger.debug("saving tool cache %s", self.tool_cache)
                        json.dump(tool_list, f, cls=ToolInfoEncoder)
            # read saved tools and return
            self.logger.debug(
                f"Remote update time: {timeit.default_timer() - get_fetch_start} s"
            )
            return self.read_tool_cache()

    def read_tool_cache(self) -> Dict[str, ToolInfo]:
        """Read the local tool cache file"""
        if not self.tool_cache.exists():
            return {}
        r = {}
        with self.tool_cache.open("r") as f:
            root_json = json.load(f)
            for name, j in root_json.items():
                r[name] = ToolInfo(
                    name,
                    updated=parse_file_time(j["updated"]),
                    location=j.get("location"),
                    versions=[
                        VersionInfo(
                            ver.get("version"),
                            ver.get("source"),
                            set(ver.get("tags")),
                            ver.get("updated"),
                            size=ver.get("size"),
                        )
                        for ver in j.get("versions")
                    ]
                    if j.get("versions")
                    else [],
                    description=j.get("description", ""),
                )
        return r

    async def list_versions(
        self,
        tool: str = "",
        toJSON: bool = False,
        only_updates: bool = False,
        force_refresh: bool = False,
    ):
        tools_loc = self.configuration.get("tools_repo_path", "")
        checker = self.configuration.get("versions", {})
        meta_filename = checker.get("metadata_filename", "meta.json")
        disable_remote = checker.get("disable_remote", False)
        mfile_p = checker.get("cache_path", "")
        maintainer = VersionMaintainer(
            self.configuration.get("tokens", None),
            meta_filename=meta_filename,
            metafiles_location=tools_loc,
            cachefiles_location=mfile_p,
            disable_remote_download=disable_remote,
            force_refresh=force_refresh,
        )
        versions = {}
        if tool:
            local_tools, remote_tools = await self.get_local_remote_tools()
            l_tool = local_tools.get(tool, "")
            r_tool = remote_tools.get(tool, "")
            if l_tool or r_tool:
                l_tool, r_tool = maintainer.get_versions_single_tool(
                    tool, l_tool, r_tool
                )
                versions = await maintainer._list_versions_single(
                    l_tool, r_tool, only_updates
                )
            else:
                raise FileNotFoundError(f"Given tool {tool} not found locally or remotely.")
        else:
            remote_tools = await self.list_tools_registry()
            # Remote tools, with included upstream version information
            remote_tools_with_origin_version = await maintainer._check_upstream_versions(
                remote_tools
            )
            # Local tools, without checking
            local_tools = await self.list_tools_local_images()
            for t in remote_tools_with_origin_version:
                r_tool = remote_tools_with_origin_version.get(
                    t
                )  # Contains also upstream version info
                l_tool = local_tools.get(t, "")
                t_info = await maintainer._list_versions_single(
                    l_tool, r_tool, only_updates
                )
                if t_info:
                    versions[t] = t_info

        if toJSON:
            return json.dumps(versions)
        else:
            return versions

    def _get_hub_session_cookies(self, s: requests.Session):
        """
        Gets JWT and CSRF token for making authorized requests for Docker Hub
        Updates request Session object with valid header

        It seems Docker Hub is using cookie-to-header pattern as
        extra CSRF protection, header named as 'X-CSRFToken'
        """

        LOGIN_URI = self.hub_url + "/users/login/"
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
        resp = s.post(LOGIN_URI, json=data, headers=headers)
        if resp.status_code == 200:
            s.headers.update({"X-CSRFToken": s.cookies.get("csrftoken")})
        else:
            raise PermissionError(f"Failed to fetch JWT and CSRF Token: {resp.content}")

    def update_readme_all_tools(self,):
        """
        Iterate over all directories, and attempt to push
        README for corresponding repository in DockerHub
        """
        if not self.tools_repo_path:
            raise RuntimeError("'Tools' repository path must be defined.'")
        fails = []
        with requests.Session() as s:
            self._get_hub_session_cookies(s)
            for tool_path in self.tools_repo_path.iterdir():
                if tool_path.is_dir() and not (tool_path.stem.startswith(("_", "."))):
                    tool_name = tool_path.stem
                    if not self.update_readme_single_tool(tool_name, s):
                        fails.append(tool_name)
            if fails:
                self.logger.info(f"Not every README updated: {','.join(fails)}")
            else:
                self.logger.info("README of every tool updated.")

    def update_readme_single_tool(
        self, tool_name: str, s: requests.Session = None, prefix="cincan/"
    ) -> bool:
        """
        Upload README  and description of tool into Docker Hub.
        Description is first header (H1) of README.

        Return True on successful update, False otherwise
        """
        if not s:
            s = requests.Session()
            self._get_hub_session_cookies(s)

        MAX_SIZE = 25000
        MAX_DESCRIPTION_LENGTH = 100
        REPOSITORY_URI = self.hub_url + f"/repositories/{prefix + tool_name}/"
        readme_path = self.tools_repo_path / tool_name / "README.md"
        if readme_path.is_file():
            if readme_path.stat().st_size <= MAX_SIZE:
                with open(readme_path, "r") as f:
                    content = f.read()
                    description = ""
                    for line in content.splitlines():
                        if line.lstrip().startswith("# "):
                            description = line.lstrip()[2:]
                            break
                    if len(description) > MAX_DESCRIPTION_LENGTH:
                        description = ""
                        self.logger.warning(
                            f"Too long description for tool {tool_name}. Not set."
                        )
                    data = {
                        "full_description": content,
                        "description": description,
                    }

                    resp = s.patch(REPOSITORY_URI, json=data)
                    if resp.status_code == 200:
                        self.logger.info(
                            f"README and description updated for {tool_name}"
                        )
                        return True
                    else:
                        self.logger.error(
                            f"Something went wrong with updating tool {tool_name}: {resp.status_code} : {resp.content}"
                        )
            else:
                self.logger.error(
                    f"README size of {tool_name} exceeds the maximum allowed {MAX_SIZE} bytes for tool {tool_name}"
                )
        else:
            self.logger.warning(f"No README file found for tool {tool_name}.")
        self.logger.warning(f"README not updated for tool {tool_name}")
        return False
