from cincanregistry.registry._registry import RemoteRegistry
from cincanregistry.utils import parse_file_time, split_tool_tag
from cincanregistry.models.tool_info import ToolInfo, ToolInfoEncoder
from cincanregistry.models.version_info import VersionInfo
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import asyncio
import requests
import docker
import base64
import json


class DockerHubRegistry(RemoteRegistry):
    """
    Inherits RemoteRegistry class to get implementation of
    Docker Registry HTTP V2 API: https://docs.docker.com/registry/spec/api/

    Adds client for external API of Docker Hub in addition of default registry
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry_name = "Docker Hub"
        self.registry_root = "https://registry.hub.docker.com"
        # Page size for Docker Hub
        self.max_page_size: int = 1000
        self._set_auth_and_service_location()

    def _get_hub_session_cookies(self):
        """
        Gets JWT and CSRF token for making authorized requests for Docker Hub (not image registry)
        Updates request Session object with valid header

        It seems Docker Hub is using cookie-to-header pattern as
        extra CSRF protection, header named as 'X-CSRFToken'
        """

        login_uri = f"{self.registry_root}/{self.schema_version}/users/login/"
        config = docker.utils.config.load_general_config()
        auths = (
            iter(config.get("auths")) if config.get("auths") else None
        )
        if auths:
            auth = {key: value for key, value in config.get("auths").items() if "docker.io" in key}
            if auth:
                token = next(iter(auth.items()))[1].get("auth")
                username, password = (
                    base64.b64decode(token).decode("utf-8").split(":", 1)
                )
            else:
                raise PermissionError(
                    "Unable to find Docker Hub credentials. Please use 'docker login' to log in."
                )
        else:
            raise PermissionError(
                "Unable to find any credentials. Please use 'docker login' to log in."
            )
        data = {"username": username, "password": password}
        headers = {
            "Content-Type": "application/json",  # redundant because json as data parameter
        }
        resp = self.session.post(login_uri, json=data, headers=headers)
        if resp.status_code == 200:
            self.session.headers.update({"X-CSRFToken": self.session.cookies.get("csrftoken")})
        else:
            raise PermissionError(f"Failed to fetch JWT and CSRF Token: {resp.content}")

    def fetch_tags(self, tool: ToolInfo, update_cache: bool = False
                   ):
        """
        Fetch remote data to update a tool info. Gives more information than using regular registry /tags/list method
        Applies only to Docker Hub
        """

        self.logger.info("fetch %s...", tool.name)
        tool_name, tool_tag = split_tool_tag(tool.name)
        params = {"page_size": self.max_page_size}
        tags_req = self.session.get(
            f"{self.registry_root}/{self.schema_version}/repositories/{tool_name}/tags",
            params=params,
            # headers={
            # "Host": self.registry_host
            # },
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
            available_versions = self.update_version_from_manifest_by_tags(tool_name, tag_names)

        else:
            self.logger.error(f"No tags found for tool {tool_name} for unknown reason.")
            return
        tool.versions = available_versions
        tool.updated = datetime.now()
        if update_cache:
            self.update_cache_by_tool(tool)

    async def get_tools(self, defined_tag: str = "") -> Dict[str, ToolInfo]:
        """List tools from registry with help of local c/ache"""
        # get_fetch_start = timeit.default_timer()
        fresh_resp = None
        # Get fresh list of tools from remote registry
        try:
            params = {"page_size": 1000}
            fresh_resp = self.session.get(
                f"{self.registry_root}/{self.schema_version}/repositories/cincan/", params=params
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
                    self.registry_name,
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
                                executor, self.fetch_tags, t
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
                    tool_list[self.CACHE_VERSION_VAR] = self.tool_cache_version
                    json.dump(tool_list, f, cls=ToolInfoEncoder)
            # read saved tools and return
            # self.logger.debug(
            #     f"Remote update time: {timeit.default_timer() - get_fetch_start} s"
            # )
            return self.read_tool_cache()
