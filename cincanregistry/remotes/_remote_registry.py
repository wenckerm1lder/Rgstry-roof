import asyncio
from urllib.parse import urlparse
import docker
import json
import base64
import re
from abc import abstractmethod
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List, Dict, Callable, Union
import requests

from cincanregistry import ToolInfo, VersionInfo
from cincanregistry._registry import RegistryBase
from cincanregistry.models.manifest import ImageConfig, ManifestV2
from cincanregistry.utils import parse_file_time


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
        self.image_prefix: str = ""
        self.cincan_namespace: str = ""
        self.full_prefix: str = ""
        # Url for other endpoint (Non-image-registry)
        self.custom_uri: str = ""
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
        """Close requests session if it exists"""
        if self.session:
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

    def _get_daemon_credentials_for_registry(self):

        config = docker.utils.config.load_general_config()
        auths = (
            iter(config.get("auths")) if config.get("auths") else None
        )
        if auths:
            if self.custom_uri:
                uri = self.custom_uri
            else:
                uri = self.registry_root
            # top the domain e.g. quay.io
            top_domain = ".".join(urlparse(uri).netloc.split('.')[-2:])
            auth = {key: value for key, value in config.get("auths").items() if top_domain in key}
            if auth:
                token = next(iter(auth.items()))[1].get("auth")
                username, password = (
                    base64.b64decode(token).decode("utf-8").split(":", 1)
                )
                self.username = username
                self.password = password
            else:
                raise PermissionError(
                    "Unable to find Docker Hub credentials. Please use 'docker login' to log in."
                )
        else:
            raise PermissionError(
                "Unable to find any credentials. Please use 'docker login' to log in."
            )

    def _get_registry_service_token(self, repo: str) -> str:
        """
        Gets Bearer token with 'pull' scope for single repository
        in Docker Registry HTTP API V2 by default.
        """
        if not self.auth_url and not self.registry_service:
            self._set_auth_and_service_location()
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

    def _get_version_from_image_config(self, conf: ImageConfig) -> str:
        """
        By given ImageConfig object, returns version of the tool from specific Env vale
        :param conf:
        :return:
        """
        env: List[str] = conf.config.get("Env")
        for var in env:
            if "".join(var).split("=")[0] == self.version_var:
                version = "".join(var).split("=")[1]
                return version
        return ""

    def fetch_manifest(
            self, name: str, tag: str, token: str = ""
    ) -> Union[ManifestV2, None]:
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
            }
        )
        if manifest_req.status_code != 200:
            self._docker_registry_api_error(
                manifest_req,
                f"Error when getting manifest for tool {name}. Code {manifest_req.status_code}",
            )
            return None
        return ManifestV2(manifest_req.json())

    def fetch_image_config(self, name: str, config_digest: str, token: str = "") -> Union[ImageConfig, None]:
        """
        Fetches image configuration JSON for tool by given config digest
        """

        if not token:
            token = self._get_registry_service_token(name)
        try:
            config_res = self.session.get(
                f"{self.registry_root}/{self.schema_version}/{name}/blobs/{config_digest}",
                headers={
                    "Authorization": f"{self.auth_digest_type} {token}",
                    "Accept": f"application/vnd.docker.container.image.v1+json",
                }
            )
            if config_res and config_res.status_code == 200:
                return ImageConfig(config_res.json())
            else:
                self.logger.warning(f"Unable to get container configuration for tool {name} with digest {config_digest}"
                                    f"response code: {config_res.status_code}")

        except requests.ConnectionError as e:
            self.logger.error(e)
        return None

    async def update_tools_in_parallel(self, tools: Dict[str, ToolInfo], fetch_function: Callable):
        """
        Updates information of tools based on given list by querying all manifests for available tags
        """

        old_tools = self.read_tool_cache()

        updated = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            loop = asyncio.get_event_loop()
            tasks = []
            for t in tools.values():
                if (
                        t.name not in old_tools
                        or t.updated > old_tools[t.name].updated
                ):
                    tasks.append(
                        loop.run_in_executor(
                            executor, fetch_function, t
                        )
                    )
                    updated += 1
                else:
                    tools[t.name] = old_tools[t.name]
                    self.logger.debug("no updates for %s", t.name)
            for _ in await asyncio.gather(*tasks):
                pass

        # save the tool list
        if updated > 0:
            self.update_cache(tools)
        return self.read_tool_cache()

    def update_versions_from_manifest_by_tags(self, tool_name: str, tag_names: List[str]) -> List[VersionInfo]:
        """
        By given tag name list, fetches corresponding manifests and generates version info
        """
        available_versions: List[VersionInfo] = []
        # Get token only once for one tool because speed
        token = self._get_registry_service_token(tool_name)
        for t in tag_names:
            manifest = self.fetch_manifest(tool_name, t, token)
            if not manifest:
                continue
            container_config = self.fetch_image_config(tool_name, manifest.config.digest, token)
            if not container_config:
                continue
            size = sum([layer.size for layer in manifest.layers])
            if manifest:
                version = self._get_version_from_image_config(container_config)
                updated = parse_file_time(container_config.created)
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
                        size=size
                    )
                    available_versions.append(ver_info)

        return available_versions
