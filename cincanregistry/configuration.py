import json
import pathlib
import logging
from typing import Dict


class Configuration:

    def __init__(self, config_path: str = "", tools_repo_path: str = ""):
        self.logger = logging.getLogger("configuration")
        self.file: pathlib.Path = pathlib.Path(
            config_path) if config_path else pathlib.Path.home() / '.cincan' / 'registry.json'
        if self.file.is_file():
            with self.file.open() as f:
                self.values: Dict = json.load(f)
        else:
            self.logger.debug(
                f"No configuration file found for registry in location: {self.file.absolute()}"
            )
            self.values: Dict = {}
        # Maximum threads at once
        self.max_workers: int = 30
        # Tokens for different platforms, used in version checking and meta file download
        self.tokens: Dict = self.values.get("tokens", {})
        # Location for cached meta files
        self.cache_location: pathlib.Path = pathlib.Path(self.values.get("cache_path")) if self.values.get("cache_path") \
            else pathlib.Path.home() / ".cincan" / "cache"
        self.cache_lifetime: int = 24  # Cache validity in hours
        # Location for cached Docker Hub manifest information
        self.tool_cache: pathlib.Path = pathlib.Path(self.values.get("registry_cache_path")) if self.values.get(
            "registry_cache_path") else self.cache_location / "tools.json"
        self.tool_cache_version: str = "1.0"

        # Local path for 'tools' repository, used for development
        # Command line argument overrides path from conf file
        self.tools_repo_path: pathlib.Path = (pathlib.Path(tools_repo_path) if tools_repo_path else None
                                ) or (
                                   pathlib.Path(self.values.get("tools_repo_path"))
                                   if self.values.get("tools_repo_path")
                                   else None
                               )
        # Default branch in GitLab
        self.branch: str = self.values.get("branch", "master")
        # Name for meta files in GitLab
        self.meta_filename: str = self.values.get("metadata_filename", "meta.json")
        # Index file in GitLab
        self.index_file: str = self.values.get("index_filename", "index.yml")
        # Disable meta file download from GitLab
        self.disable_remote: bool = self.values.get("disable_remote", False)
        # GitLab namespace
        self.namespace: str = "cincan"
        # Docker Hub repository
        self.prefix: str = "cincan/"
        # GitLab repository
        self.project: str = "tools"
