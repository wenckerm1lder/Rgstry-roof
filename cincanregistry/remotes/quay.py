import datetime
import requests
import json
from typing import Dict, List
from cincanregistry.utils import split_tool_tag
from cincanregistry.remotes._remote_registry import RemoteRegistry
from cincanregistry import ToolInfo, Remotes


class QuayRegistry(RemoteRegistry):
    """
    Implements Quay HTTP API partially (enough to be able to list repositories get some information),
    docs available in here https://docs.quay.io/api/swagger/#!/repository/listRepos
    """

    def __init__(self, *args, **kwargs):
        super(QuayRegistry, self).__init__(*args, **kwargs)
        self.registry_name = Remotes.QUAY.value
        self.registry_root = "https://quay.io"
        self.image_prefix = "quay.io"
        self.cincan_namespace: str = "cincan"
        self.full_prefix = f"{self.image_prefix}/{self.cincan_namespace}"

    def _quay_api_error(self, resp: requests.Response):
        """ Error schema:
        {
          "status": 0,
          "error_message": "string",
          "title": "string",
          "error_type": "string",
          "detail": "string",
          "type": "string"
        }
        """
        try:
            resp = resp.json()
            self.logger.error(f'Quay API error: {resp.get("status")} - {resp.get("error_message")}')
            self.logger.error(f'Title: {resp.get("title")} Error type: {resp.get("error_type")}'
                              f'Detail: {resp.get("detail")} Type: {resp.get("type")}')
        except json.JSONDecodeError as e:
            self.logger.error(f"Non-schema response with status code: {resp.status_code} - {e}")

    def __fetch_available_tools(self, next_page: str = "", repo_kind: str = "image", popularity: bool = False,
                                last_modified: bool = True, public: bool = True, starred: bool = False,
                                namespace: str = "") -> List[Dict]:
        """
        Fetch all Docker images related to namespace
        See: https://docs.quay.io/api/swagger/#!/repository/listRepos
        """
        endpoint = "/api/v1/repository"
        params = {
            "next_page": next_page,
            "repo_kind": repo_kind,
            "popularity": popularity,
            "last_modified": last_modified,
            "public": public,
            "starred": starred,
            "namespace": namespace if namespace else self.cincan_namespace
        }
        if not next_page:
            # Remove empty param
            params.pop("next_page")
        resp = None
        try:
            resp = self.session.get(f"{self.registry_root}{endpoint}", params=params)
        except requests.exceptions.ConnectionError as e:
            self.logger.error(e)

        if resp and resp.status_code == 200:
            # For some reason 200 is returned when namespace does not exist
            self.logger.debug(f"Acquired list of tools from {self.registry_root}")
            resp_cont = resp.json()
            if not resp_cont.get("repositories"):
                self.logger.debug("Seems like namespace does not exist nor have available repositories.")
        else:
            self.logger.error(f"Failed to fetch tools from {self.registry_name}")
            self._quay_api_error(resp)
            return []
        tools_list = resp_cont.get("repositories")
        while "next_page" in resp_cont.keys():
            self.logger.debug(f"Did not fetch all tools from the {self.registry_name}. Fetching possible 100 more...")
            params["next_page"] = resp_cont.get("next_page")
            try:
                resp = self.session.get(f"{self.registry_root}{endpoint}", params=params)
                if resp and resp.status_code == 200:
                    resp_cont = resp.json()
                    tools_list += resp_cont.get("repositories")
                elif resp:
                    self._quay_api_error(resp)
                else:
                    # Should not happen..
                    self.logger.error(f"Something went wrong when fetching "
                                      f"multiple pages of tools in {self.registry_name}")
            except requests.exceptions.ConnectionError as e:
                self.logger.error(e)
                return []

        return tools_list

    async def get_tools(self, defined_tag: str = "", force_update: bool = False) -> Dict[str, ToolInfo]:
        """Get tools from remote registry. Name set without repository prefixes"""
        self._set_auth_and_service_location()
        available_tools = self.__fetch_available_tools()
        tool_list = {}
        for t in available_tools:
            # name = f"{self.image_prefix}/{t.get('namespace')}/{t.get('name')}"
            name = t.get('name')
            timestamp = t.get("last_modified")
            description = t.get("description")
            tool_list[name] = ToolInfo(name, datetime.datetime.fromtimestamp(timestamp),
                                       self.registry_name, description=description)
        return await self.update_tools_in_parallel(tool_list, self.fetch_tags, force_update)

    def fetch_tags(self, tool: ToolInfo, update_cache: bool = False):
        """
        Fetches available tags for single tool from quay.io HTTP API
        See: https://docs.quay.io/api/swagger/#!/repository/getRepo
        """
        if not self.auth_url:
            self._set_auth_and_service_location()
        # In case name includes tag, separate it
        self.logger.info("fetch %s...", tool.name)
        tool_name, tool_tag = split_tool_tag(tool.name)
        # Use name without registry prefix e.g. quay.io
        # name_without_prefix = "/".join(tool_name.split("/")[-2:])
        name_without_prefix = f"{self.cincan_namespace}/{tool_name}"
        endpoint = f"{self.registry_root}/api/v1/repository/{name_without_prefix}"
        params = {
            "includeTags": True,
            "includeStats": False
        }
        resp = None
        try:
            resp = self.session.get(endpoint, params=params)
        except requests.exceptions.ConnectionError as e:
            self.logger.error(e)
        if resp and resp.status_code == 200:
            resp_cont = resp.json()
            tags = resp_cont.get("tags")
            tag_names = tags.keys()
            if tag_names:
                available_versions = self.update_versions_from_manifest_by_tags(name_without_prefix, tag_names)
            else:
                self.logger.error(f"No tags found for tool {tool_name}.")
                return
            tool.versions = available_versions
            tool.updated = datetime.datetime.now()
            if update_cache:
                self.update_cache_by_tool(tool)

        else:
            self.logger.error(f"Failed to fetch tags for image {tool.name} - not updated")
            if resp:
                self._quay_api_error(resp)
            return
