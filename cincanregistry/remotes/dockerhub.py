from datetime import datetime
from typing import Dict

import requests

from cincanregistry import Remotes
from cincanregistry.models.tool_info import ToolInfo
from cincanregistry.remotes._remote_registry import RemoteRegistry
from cincanregistry.utils import parse_file_time, split_tool_tag


class DockerHubRegistry(RemoteRegistry):
    """
    Inherits RemoteRegistry class to get implementation of
    Docker Registry HTTP V2 API: https://docs.docker.com/registry/spec/api/

    Adds client for external API of Docker Hub in addition of default registry
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry_name = Remotes.DOCKERHUB.value
        self.registry_root = "https://registry.hub.docker.com"
        self.image_prefix = ""
        self.cincan_namespace = "cincan"
        self.full_prefix = self.cincan_namespace
        self.custom_uri = "https://docker.io"
        # Page size for Docker Hub
        self.max_page_size: int = 1000

    def _get_hub_session_cookies(self):
        """
        Gets JWT and CSRF token for making authorized requests for Docker Hub (not image registry)
        Updates request Session object with valid header

        It seems Docker Hub is using cookie-to-header pattern as
        extra CSRF protection, header named as 'X-CSRFToken'
        """

        login_uri = f"{self.registry_root}/{self.schema_version}/users/login/"
        self._get_daemon_credentials_for_registry()
        data = {"username": self.username, "password": self.password}
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
        if not self.auth_url:
            self._set_auth_and_service_location()
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
        if tag_names:
            available_versions = self.update_versions_from_manifest_by_tags(tool_name, tag_names)

        else:
            self.logger.error(f"No tags found for tool {tool_name} for unknown reason.")
            return
        tool.versions = available_versions
        tool.updated = datetime.now()
        if update_cache:
            self.update_cache_by_tool(tool)

    async def get_tools(self, defined_tag: str = "", force_update: bool = False) -> Dict[str, ToolInfo]:
        """List tools from registry with help of local c/ache"""
        # get_fetch_start = timeit.default_timer()
        fresh_resp = None
        # Get fresh list of tools from remote registry
        self._set_auth_and_service_location()
        try:
            params = {"page_size": 1000}
            fresh_resp = self.session.get(
                f"{self.registry_root}/{self.schema_version}/repositories/{self.cincan_namespace}/", params=params
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

            return await self.update_tools_in_parallel(tool_list, self.fetch_tags, force_update)
