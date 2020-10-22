from typing import Dict, List
from cincanregistry.registry._registry import RemoteRegistry
from cincanregistry import ToolInfo


class QuayRegistry(RemoteRegistry):
    """
    Implements Quay HTTP API partially (enough to be able to list repositories),
    docs available in here https://docs.quay.io/api/swagger/#!/repository/listRepos
    """

    def __init__(self, *args, **kwargs):
        super(QuayRegistry, self).__init__(*args, **kwargs)
        self.registry_name = "Quay"
        self.registry_root = "https://quay.io"
        self._set_auth_and_service_location()

    def __fetch_available_tools(self, next_page: str = "", repo_kind: str = "image", popularity: bool = False,
                                last_modified: bool = True, public: bool = True, starred: bool = False,
                                namespace: str = "") -> List[Dict]:
        tools_list: List[Dict] = []
        endpoint = "/api/v1/repository"
        params = {
            "next_page": next_page,
            "repo_kind": repo_kind,
            "popularity": popularity,
            "last_modified": last_modified,
            "public": public,
            "starred": starred,
            "namespace": namespace if namespace else self.config.namespace
        }
        if not next_page:
            params.pop("next_page")
        resp = self.session.get(f"{self.registry_root}{endpoint}", params=params)
        if resp.status_code == 200:
            self.logger.debug(f"Acquired list of tools from {self.registry_root}")
        else:
            self.logger.error(f"Failed to fetch tools from {self.registry_name}")
        resp_cont = resp.json()
        tools_list = resp_cont.get("repositories")
        while "next_page" in resp_cont.keys():
            self.logger.debug(f"Did not fetch all tools from the {self.registry_name}. Fetching 100 more...")
            params["next_page"] = resp_cont.get("next_page")
            resp = self.session.get(f"{self.registry_root}{endpoint}", params=params)
            resp_cont = resp.json()
            tools_list += resp_cont.get("repositories")

        return tools_list

    async def get_tools(self, defined_tag: str = "") -> Dict[str, ToolInfo]:
        self.__fetch_available_tools()
        pass

    def fetch_tags(self, tool: ToolInfo, update_cache: bool = False):
        pass
