import re
import json
import logging
import pathlib
from typing import Any, Dict, Union, List
from abc import ABCMeta, abstractmethod
import requests
from cincanregistry import ToolInfo, ToolInfoEncoder, VersionInfo
from ..utils import parse_file_time
from ..configuration import Configuration
from .manifest import ManifestV2


class RegistryBase(metaclass=ABCMeta):
    """
    Base class for local and remote registry

    Provides some methods for handling cache

    # TODO make sqlite3 database instead of JSON...
    """
    VER_UNDEFINED = "undefined"
    CACHE_VERSION_VAR = "__cache_version"

    def __init__(self,
                 config_path: str = "",
                 tools_repo_path: str = "",
                 version_var: str = "TOOL_VERSION"):
        self.logger: logging.Logger = logging.getLogger("registry")
        self.registry_name: str = ""
        self.config: Configuration = Configuration(config_path, tools_repo_path)
        self.version_var: str = version_var
        self.tool_cache: pathlib.Path = self.config.tool_cache
        self.tool_cache_version: str = self.config.tool_cache_version
        self.tools_repo_path: pathlib.Path = self.config.tools_repo_path

    @abstractmethod
    async def get_tools(self, defined_tag: str = "") -> Dict[str, ToolInfo]:
        pass

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


class RemoteRegistry(RegistryBase):
    """
    Implements client for Docker Registry HTTP V2 API
    https://docs.docker.com/registry/spec/api/
    """

    def __init__(self, *args, **kwargs):
        super(RemoteRegistry, self).__init__(*args, **kwargs)
        self.schema_version: str = "v2"
        self.registry_root: str = ""
        self.registry_service: str = ""
        self.auth_digest_type: str = "Bearer"
        self.auth_url: str = ""
        self.max_workers: int = self.config.max_workers
        # Using single Requests.Session instance here
        self.session: requests.Session = requests.Session()
        # Adapter allows more simultaneous connections
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=self.max_workers)
        self.session.mount("https://", adapter)

    @abstractmethod
    def fetch_tags(self, tool: ToolInfo, update_cache: bool = False):
        pass

    def __del__(self):
        self.session.close()

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
            self, name: str, tag: str, token: str = ""
    ) -> Dict[str, Any]:
        """
        Fetch docker image manifest information by tag
        Manifest version 1 is deprecated, only V2 used.

        TODO add maybe "fat manifest" support
        """

        # Get authentication token for tool with pull scope if not provided
        if not token:
            token = self._get_registry_service_token(name)

        manifest_req = self.session.get(
            f"{self.registry_root}/{self.schema_version}/{name}/manifests/{tag}",
            headers={
                "Authorization": f"{self.auth_digest_type} {token}",
                "Accept": f"application/vnd.docker.distribution.manifest.v2+json",
            },
        )
        if manifest_req.status_code != 200:
            self._docker_registry_api_error(
                manifest_req,
                f"Error when getting manifest for tool {name}. Code {manifest_req.status_code}",
            )
            return {}
        return ManifestV2(manifest_req.json())

    def fetch_container_config(self, config_digest:str ):


    def update_version_from_manifest_by_tags(self, tool_name: str, tag_names: List[str]) -> List[VersionInfo]:
        """
        By given tag name list, fetches corresponding manifests and generates version info
        """
        available_versions: List[VersionInfo] = []
        # Get token only once for one tool because speed
        token = self._get_registry_service_token(tool_name)
        for t in tag_names:
            manifest = self.fetch_manifest(tool_name, t, token)
            if manifest:
                version, updated = self._get_version_from_manifest(manifest)
                if not version:
                    version = self.VER_UNDEFINED
                match = [v for v in available_versions if version == v.version]
                if match:
                    next(iter(match)).tags.add(t)
                else:
                    ver_info = VersionInfo(
                        version,
                        self.registry_name,
                        {t},
                        updated,
                        # size=t.get("full_size"),
                    )
                    available_versions.append(ver_info)

        return available_versions
