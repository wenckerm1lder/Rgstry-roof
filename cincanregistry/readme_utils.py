import logging
import pathlib
from abc import ABCMeta, abstractmethod

from requests import Response

from cincanregistry.remotes import DockerHubRegistry, QuayRegistry
from cincanregistry.utils import read_index_file


class ReadmeHandler(metaclass=ABCMeta):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs
        )
        self.logger = logging.getLogger(__name__)
        if not self.tools_repo_path:
            raise RuntimeError("'Tools' repository path must be defined.'")
        self.index_path = self.tools_repo_path / self.config.index_file
        # Some numbers
        self.max_size: int = 100000
        self.max_description_size: int = 200
        # Set available tools
        self.tool_locations = read_index_file(self.index_path)

    def update_readme_all_tools(self, ):
        """
        Iterate over all directories, and attempt to push
        README for corresponding repository in registry
        """
        fails = []
        for tools_root in self.tool_locations:
            # Iterate over different locations: stable or dev tools etc.
            for tool_path in (self.tools_repo_path / tools_root).iterdir():
                # Exclude files starting with '_' and '.'
                if tool_path.is_dir() and not (tool_path.stem.startswith(("_", "."))):
                    tool_name = tool_path.stem
                    if not self.update_readme_single_tool(tool_name, tool_path, many=True):
                        fails.append(tool_name)
        if fails:
            self.logger.info(f"Not every README updated: {','.join(fails)}")
        else:
            self.logger.info("README of every tool updated.")

    def get_readme_path(self, tool_path: pathlib.Path, tool_name: str) -> pathlib.Path:

        readme_path = pathlib.Path()
        if tool_path:
            readme_path = tool_path / "README.md"
        else:
            found = False
            for tools_root in self.tool_locations:
                tmp_path = self.tools_repo_path / tools_root / tool_name / "README.md"
                if tmp_path.is_file():
                    if found:
                        raise RuntimeError(f"Tool {tool_name} has multiple locations. Should not be possible. Fix it.")
                    else:
                        readme_path = tmp_path
                        found = True
        return readme_path

    def update_readme_single_tool(
            self, tool_name: str, tool_path: pathlib.Path = "", many: bool = False, prefix="cincan/"
    ) -> bool:
        """
        Upload possible README and description of tool into Container Registry.
        Description is first header (H1) of README.

        Return True on successful update, False otherwise
        """
        if not self.tools_repo_path:
            raise RuntimeError("'Tools' repository path must be defined.'")

        readme_path = self.get_readme_path(tool_path, tool_name)
        if readme_path.is_file():
            if readme_path.stat().st_size <= self.max_size:
                with readme_path.open("r") as f:
                    content = f.read()
                    description = ""
                    for line in content.splitlines():
                        if line.lstrip().startswith("# "):
                            description = line.lstrip()[2:]
                            break
                    if len(description) > self.max_description_size:
                        description = ""
                        self.logger.warning(
                            f"Too long description for tool {tool_name}. Not set."
                        )

                    resp = self.post_data(tool_name, prefix, description=description, content=content)
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
                    f"README size of {tool_name} exceeds the maximum allowed {self.max_size} bytes for tool {tool_name}"
                )
        else:
            self.logger.warning(
                f"No README file found for tool {tool_name} in path {readme_path}."
            )
        self.logger.warning(f"README not updated for tool {tool_name}")
        return False

    @abstractmethod
    def post_data(self, tool_name: str, prefix: str, description: str = "", content: str = "") -> Response:
        pass


class HubReadmeHandler(DockerHubRegistry, ReadmeHandler):
    """
    Class for updating README files and description in Docker Hub.
    """

    def __init__(self, *args, **kwargs):
        DockerHubRegistry.__init__(self, *args, **kwargs)
        ReadmeHandler.__init__(self)
        self.max_size = 25000
        self.max_description_size = 100
        # Update cookie headers
        self._get_hub_session_cookies()

    def post_data(self, tool_name: str, prefix: str, description: str = "", content: str = "") -> Response:
        """Post data to update readme and description, return true on success"""
        repository_uri = f"{self.registry_root}/{self.schema_version}/repositories/{prefix + tool_name}/"

        data = {
            "full_description": content,
            "description": description,
        }

        resp = self.session.patch(repository_uri, json=data)
        return resp


class QuayReadmeHandler(QuayRegistry, ReadmeHandler):
    """Update description in Quay Registry Seems like there is only one field for description."""

    def __init__(self, *args, **kwargs):
        QuayRegistry.__init__(self, *args, **kwargs)
        ReadmeHandler.__init__(self)

    def post_data(self, tool_name: str, prefix: str, description: str = "", content: str = "") -> Response:
        if not self.tools_repo_path:
            raise RuntimeError("'Tools' repository path must be defined.'")

        repository_uri = f"{self.registry_root}/api/v1/repository/{prefix + tool_name}"
        self._get_daemon_credentials_for_registry()
        self.session.headers.update(
            {"Authorization": f'Bearer {self.password if self.password else self.config.tokens.get("Quay")}'})
        data = {
            "description": description
        }
        resp = self.session.put(repository_uri, json=data)
        return resp
