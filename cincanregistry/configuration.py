import logging
import pathlib
from enum import Enum
from typing import Dict

import yaml


class Remotes(Enum):
    _order_ = 'QUAY DOCKERHUB'  # Order is important, the first is default
    QUAY = "Quay"
    DOCKERHUB = "DockerHub"

    def __str__(self):
        return self.value


class Configuration:

    def __init__(self, config_path: str = "", tools_repo_path: str = ""):
        self.logger = logging.getLogger("configuration")
        self.home = pathlib.Path.home() / '.cincan'
        self.file: pathlib.Path = pathlib.Path(
            config_path) if config_path else self.home / 'registry.yaml'
        if self.file.is_file():
            with self.file.open() as f:
                try:
                    self.values: Dict = yaml.load(f, Loader=yaml.SafeLoader)
                except yaml.parser.ParserError as e:
                    self.logger.error(f"Unable to load configuration file: {e}")
                    exit(1)
        else:
            self.logger.debug(
                f"No configuration file found for registry in location: {self.file.absolute()}"
            )
            self.values: Dict = {}
        # Override from cmd only if non-default used
        self.registry = Remotes(self.values.get("registry")) if self.values.get("registry") else list(Remotes)[0]
        # Maximum threads at once
        self.max_workers: int = 30
        # Tokens for different platforms used in version checking and meta file download
        self.tokens: Dict = self.values.get("tokens", {})
        # Lowercase keys to mach upstream checkers
        self.tokens = dict((k.lower(), v) for k, v in self.tokens.items())
        # Location for cached meta files
        self.cache_location: pathlib.Path = pathlib.Path(self.values.get("cache_path")) \
            if self.values.get("cache_path") \
            else self.home / "cache"
        self.tool_db = self.cache_location / "tooldb.sqlite"
        self.cache_lifetime: int = 24  # Cache validity in hours
        # Location for cached Docker Hub manifest information
        self.tool_cache: pathlib.Path = pathlib.Path(self.values.get("registry_cache_path")) if self.values.get(
            "registry_cache_path") else self.cache_location / "tools.json"
        self.tool_cache_version: str = "1.1"

        # Local path for 'tools' repository, used for development
        # Command line argument overrides path from conf file
        self.tools_repo_path: pathlib.Path = (pathlib.Path(tools_repo_path) if tools_repo_path else None) or (
            pathlib.Path(self.values.get("tools_repo_path"))
            if self.values.get("tools_repo_path")
            else None
        )
        # Default tag representing latest image
        self.tag = self.values.get("latest-tag", "latest")

        # Default branch in GitLab
        self.branch: str = self.values.get("branch", "master")
        # Name for meta files in GitLab
        self.meta_filename: str = self.values.get("metadata_filename", "meta.json")
        self.meta_max_size: int = 1000 * 5  # In bytes, metafile max size
        # Index file in GitLab
        self.index_file: str = self.values.get("index_filename", "index.yml")
        # Disable meta file download from GitLab
        self.disable_remote: bool = self.values.get("disable_remote", False)
        # Namespace for fetching list of tools
        self.namespace: str = self.values.get("namespace", "")
        if self.namespace and isinstance(str, self.namespace):
            self.namespace = self.namespace.lower()
        # GitLab repository
        self.project: str = "tools"
        # Create default folders
        self.home.mkdir(parents=True, exist_ok=True)
        self.cache_location.mkdir(parents=True, exist_ok=True)
        # Generate config file with default values, using yaml format to enable comments
        if not self.values:
            self.logger.debug("Generating configuration file with default values.")
            # Make directory if it does not exist
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with self.file.open("w") as f:
                print(f"# Configuration file of the cincan-registry Python module\n", file=f)
                print(f"registry: {self.registry}  # Default registry wherefrom tools are used", file=f)
                # print(f"namespace: {self.namespace}
                # Overrides default cincan namespaces for tool registries", file=f)
                print(f"cache_path: {self.cache_location} # All cache files are in here", file=f)
                print(f"registry_cache_path: {self.tool_cache} # Contains details about tools "
                      f"(no version information)", file=f)
                print(f"tools_repo__path: {self.tools_repo_path} # Path for local 'tools'"
                      f" repository (Use metafiles from there)", file=f)
                # print(f"latest-tag: {self.tag}# Default tag representing latest image", file=f)

                print(f"\n# Configuration related to tool metafiles.", file=f)
                print(f"\nbranch: {self.branch} # Branch in GitLab for acquiring metafiles", file=f)
                print(f"meta_filename: {self.meta_filename} # Filename of metafile in GitLab", file=f)
                print(f"index_filename: {self.index_file} # Filename of index file in GitLab", file=f)
                print(f"disable_remote: {self.disable_remote} # Disable fetching metafiles from GitLab", file=f)
                print(f"\ntokens: # Possible authentication tokens to Quay, GitLab, GitHub and so on. Quay token is"
                      f" used for README updating.",
                      file=f)
                print("    quay: ''", file=f)
                print(file=f)
