import docker
import docker.errors
import logging
import pathlib
import requests
import json
import datetime
import timeit
import asyncio
import re
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Iterable, Tuple
from pprint import pprint
from .checkers import classmap
from .toolinfo import ToolInfo, VersionInfo
from .utils import parse_data_types, parse_json_time, format_time, split_tool_tag


VERSION_VARIABLE = "TOOL_VERSION"
REGISTRY_CONF = pathlib.Path.home() / ".cincan/registry.json"
VER_UNDEFINED = "undefined"
REMOTE_REGISTRY = "Dockerhub"
LOCAL_REGISTRY = "Docker Server"


def tools_to_json(tools: Iterable[ToolInfo]) -> Dict[str, Any]:
    """Write tool info into JSON format"""
    r = {}
    for t in tools:
        td = {"updated": format_time(t.updated)}
        if t.destination:
            td["destination"] = t.destination
        if t.description:
            td["description"] = t.description
        if t.versions:
            td["versions"] = [
                {
                    "version": ver.version,
                    "source": ver.source,
                    "tags": [t for t in ver.tags],
                    "updated": ver.updated,
                }
                for ver in t.versions
            ]
        r[t.name] = td
    return r


class ToolRegistry:
    """A tool registry"""

    def __init__(self):
        self.logger = logging.getLogger("registry")
        self.client = docker.from_env()
        self.tool_cache = pathlib.Path.home() / ".cincan" / "tools.json"
        self.schema_version = "v2"
        self.hub_url = f"https://hub.docker.com/{self.schema_version}"
        self.auth_url = "https://auth.docker.io/token"
        self.registry_service = "registry.docker.io"
        self.registry_host = "registry.hub.docker.com"
        self.registry_url = f"https://{self.registry_host}/{self.schema_version}"
        self.max_workers = 30
        self.max_page_size = 1000
        try:
            with open(REGISTRY_CONF) as f:
                self.configuration = json.load(f)
        except IOError:
            self.logger.warning(
                f"No configuration file found for registry in location: {REGISTRY_CONF}"
            )
            self.configuration = {}

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
        self, manifest: dict, ver_variable: str = VERSION_VARIABLE
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
                if "".join(i).split("=")[0] == ver_variable:
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
        # TODO rework this method, remote and local listing changed

        local_tools, remote_tools = self.get_local_remote_tools(defined_tag)
        use_tools = {}
        merged_tools_dic = {**local_tools, **remote_tools}
        for i in set().union(local_tools.keys(), remote_tools.keys()):
            if not defined_tag or defined_tag in merged_tools_dic[i].tags:
                pass
            else:
                self.logger.debug(
                    f"Provided tag '{defined_tag}' not found for image {i}."
                )
                continue
            if i not in local_tools:
                use_tools[i] = remote_tools[i]
                self.logger.debug("using remote image for %s", use_tools[i].name)
            elif i not in remote_tools:
                use_tools[i] = local_tools[i]
                self.logger.debug("using local image for %s", use_tools[i].name)
            else:
                local = local_tools[i]
                remote = remote_tools[i]
                if local.updated >= remote.updated:
                    use_tools[i] = local
                    self.logger.debug("using local image for %s", use_tools[i].name)
                else:
                    use_tools[i] = remote
                    self.logger.debug("using remote image for %s", use_tools[i].name)
                # assume all unique local tags are newer than remote ones
                use_tags = [i for i in local.tags if i not in remote.tags] + remote.tags
                use_tools[i].tags = use_tags
                # description only in registry, not locally
                use_tools[i].description = remote_tools[i].description
        if not use_tools:
            self.logger.info(f"No single tool found with tag `{defined_tag}`.")
        return use_tools

    async def list_tools_local_images(
        self,
        defined_tag: str = "",
        prefix: str = "cincan/",
        version_var: str = VERSION_VARIABLE,
        default_ver: str = VER_UNDEFINED,
    ) -> Dict[str, ToolInfo]:
        """
        List tools from the locally available docker images
        Only tools with starts with 'prefix' are listed.
        Additionally, if tag is defined, tool must have this tag
        before it is listed.
        """
        images = self.client.images.list(filters={"dangling": False})
        # images oldest first (tags are listed in proper order)
        images.sort(key=lambda x: parse_json_time(x.attrs["Created"]), reverse=True)
        ret = {}
        for i in images:
            # print(i.attrs.get("ContainerConfig").get("Env"))
            if len(i.tags) == 0:
                continue  # not sure what these are...
            updated = parse_json_time(i.attrs["Created"])

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
                        environment = i.attrs.get("ContainerConfig").get("Env")
                        for var in environment:
                            if "".join(var).split("=")[0] == version_var:
                                version = "".join(var).split("=")[1]
                                break
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
                                    )
                                )
                        else:
                            ver_info = VersionInfo(
                                version, LOCAL_REGISTRY, set(stripped_tags), updated
                            )
                            ret[name] = ToolInfo(
                                name, updated, "local", versions=[ver_info]
                            )
                            self.logger.debug(
                                f"Added tool {name} based on tag {t} with version {version}"
                            )
                            continue
                    else:
                        continue
        return ret

    def fetch_remote_data(
        self, session: requests.Session, tool: ToolInfo
    ) -> Dict[str, Any]:
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
            key=lambda x: parse_json_time(x["last_updated"]),
            reverse=True,
        )
        tag_names = list(map(lambda x: x["name"], tags_sorted))

        manifest_latest = {}
        first_run = True
        if tool.name.count(":") == 0 and tag_names:
            for t in tag_names:
                manifest = self.fetch_manifest(session, tool_name, t)
                if first_run:
                    manifest_latest = manifest
                    first_run = False
                if manifest:
                    version, updated = self._get_version_from_manifest(manifest)
                    if not version:
                        version = VER_UNDEFINED
                    match = [v for v in available_versions if version == v.version]
                    if match:
                        next(iter(match)).tags.add(t)
                    else:
                        ver_info = VersionInfo(version, REMOTE_REGISTRY, {t}, updated)
                        available_versions.append(ver_info)
        else:
            manifest = self.fetch_manifest(session, tool_name, tool_tag)
            if manifest:
                manifest_latest = manifest
                version, updated = self._get_version_from_manifest(manifest)
                available_versions.append(
                    VersionInfo(version, REMOTE_REGISTRY, {t}, updated)
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
                        parse_json_time(t["last_updated"]),
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
                                    executor, self.fetch_remote_data, *(session, t)
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
                        json.dump(tools_to_json(tool_list.values()), f)
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
                    updated=parse_json_time(j["updated"]),
                    destination=j.get("destination"),
                    versions=[
                        VersionInfo(
                            ver.get("version"),
                            ver.get("source"),
                            set(ver.get("tags")),
                            ver.get("updated"),
                        )
                        for ver in j.get("versions")
                    ]
                    if j.get("versions")
                    else [],
                    description=j.get("description", ""),
                )
        return r

    def get_available_checkers(self, prefix="cincan/") -> Dict:
        """
        Gets dictionary of tools, whereas upstream/origin check is supported.
        """
        able_to_check = {}

        for tool_path in (pathlib.Path(pathlib.Path.cwd() / "tools")).iterdir():
            able_to_check[f"{prefix}{tool_path.stem}"] = tool_path
        if not able_to_check:
            self.logger.error(
                f"No single configuration for upstream check found. Something is wrong in path {pathlib.Path(pathlib.Path.cwd() / 'tools')}"
            )
        return able_to_check

    async def get_versions_single_tool(self, tool: str):
        local_tools, remote_tools = await self.get_local_remote_tools()
        l_tool = local_tools.get(tool, "")
        r_tool = remote_tools.get(tool, "")
        if l_tool or r_tool:
            tool_conf = self.get_available_checkers().get(tool)
            if not tool_conf:
                raise FileNotFoundError(f"Upstream check not implemented for {tool}.")
            if r_tool:
                self._set_single_tool_upstream_versions(tool_conf, r_tool)
            else:
                self._set_single_tool_upstream_versions(tool_conf, l_tool)
        else:
            raise FileNotFoundError(f"Given tool {tool} not found locally or remotely.")
        return l_tool, r_tool

    def _set_single_tool_upstream_versions(self, tool_path: str, tool: ToolInfo) -> str:

        with open(tool_path / f"{tool_path.stem}.json") as f:
            conf = json.load(f)
            for tool_info in conf if isinstance(conf, List) else [conf]:
                provider = tool_info.get("provider").lower()
                token = (
                    self.configuration.get("tokens").get(provider)
                    if self.configuration
                    else ""
                )
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

    async def _check_upstream_versions(self, only_local: bool = True):
        """
        Checks for available versions in upstream
        """
        able_to_check = self.get_available_checkers()
        tools = (
            await self.list_tools_local_images()
            if only_local
            else await self.list_tools_registry()
        )
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for t in tools:
                tool_path = able_to_check.get(t)
                if tool_path:
                    tool = tools.get(t)
                    loop = asyncio.get_event_loop()
                    tasks = []
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

        # print(tool_path.stem)

    async def _list_versions_single(self, l_tool: ToolInfo, r_tool: ToolInfo) -> dict:

        tool_info = {}
        tool_info["name"] = r_tool.name if r_tool else l_tool.name
        tool_info["local_version"] = l_tool.getLatest().version if l_tool else ""
        tool_info["remote_version"] = r_tool.getLatest().version
        tool_info["origin_version"] = r_tool.getOriginVersion().version
        tool_info["origin_details"] = (
            dict(r_tool.getOriginVersion().source)
            if r_tool.getOriginVersion().origin
            else ""
        )
        tool_info["other_versions"] = [
            dict(v.source) if not isinstance(v.source, str) else v.source
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
            tool_info.get("origin_version") == "Not implemented"
            and not tool_info.get("other_versions")
        ):
            pass
        elif r_latest in [v for v in r_tool.upstream_v if not v.origin]:
            pass
        else:
            self.logger.debug(
                f"Tool {r_tool.name} is not up to date with origin/installation upstream."
            )
            tool_info["updates"]["remote"] = True

        return tool_info

    async def list_versions(self, tool: str = "", toJSON: bool = False):

        versions = {}
        if tool:
            l_tool, r_tool = await self.get_versions_single_tool(tool)
            versions = await self._list_versions_single(l_tool, r_tool)
        else:
            all_tools = await self._check_upstream_versions(only_local=False)
            local_tools = await self.list_tools_local_images()
            for t in all_tools:
                r_tool = all_tools.get(t)  # Contains also upstream version info
                l_tool = local_tools.get(t, "")
                versions[t] = await self._list_versions_single(l_tool, r_tool)

        if toJSON:
            return json.dumps(versions)
        else:
            return versions
