from .registry import ToolRegistry
import requests
import logging


class HubReadmeHandler(ToolRegistry):
    """
    Class for updating README files in Docker Hub.
    """

    def __init__(self, config_path="", tools_repo_path="", version_var="TOOL_VERSION"):
        super().__init__(
            config_path=config_path,
            tools_repo_path=tools_repo_path,
            version_var=version_var,
        )
        self.logger = logging.getLogger(__name__)
        self.max_size = 25000
        self.max_description_size = 100

    def update_readme_all_tools(self, ):
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
                # Exclude files starting with '_' and '.'
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
        if not self.tools_repo_path:
            raise RuntimeError("'Tools' repository path must be defined.'")

        if not s:
            s = requests.Session()
            self._get_hub_session_cookies(s)

        repository_uri = self.hub_url + f"/repositories/{prefix + tool_name}/"
        readme_path = self.tools_repo_path / tool_name / "README.md"
        if readme_path.is_file():
            if readme_path.stat().st_size <= self.max_size:
                with open(readme_path, "r") as f:
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
                    data = {
                        "full_description": content,
                        "description": description,
                    }

                    resp = s.patch(repository_uri, json=data)
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
