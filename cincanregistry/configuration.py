import json
import pathlib
import logging


class Configuration:

    def __init__(self, config_path: str = "", tools_repo_path: str = ""):
        self.logger = logging.getLogger("configuration")
        self.file = pathlib.Path(config_path) if config_path else pathlib.Path.home() / '.cincan' / 'registry.json'
        if self.file.is_file():
            with self.file.open() as f:
                self.values = json.load(f)
        else:
            self.logger.debug(
                f"No configuration file found for registry in location: {self.file.absolute()}"
            )
            self.values = {}
        # Maximum threads at once
        self.max_workers = 30
        # Tokens for different platforms, used in version checking and meta file download
        self.tokens = self.values.get("tokens", {})
        # Location for cached meta files
        self.cache_location = pathlib.Path(self.values.get("cache_path")) if self.values.get("cache_path") \
            else pathlib.Path.home() / ".cincan" / "cache"
        self.cache_lifetime = 24  # Cache validity in hours
        # Location for cached Docker Hub manifest information
        self.tool_cache = pathlib.Path(self.values.get("registry_cache_path")) if self.values.get(
            "registry_cache_path") else self.cache_location / "tools.json"
        self.tool_cache_version = "1.0"

        # Local path for 'tools' repository, used for development
        # Command line argument overrides path from conf file
        self.tools_repo_path = (pathlib.Path(tools_repo_path) if tools_repo_path else None
                                ) or (
                                   pathlib.Path(self.values.get("tools_repo_path"))
                                   if self.values.get("tools_repo_path")
                                   else None
                               )
        # Default branch in GitLab
        self.branch = self.values.get("branch", "master")
        # Name for meta files in GitLab
        self.meta_filename = self.values.get("metadata_filename", "meta.json")
        # Index file in GitLab
        self.index_file = self.values.get("index_filename", "index.yml")
        # Disable meta file download from GitLab
        self.disable_remote = self.values.get("disable_remote", False)
        # GitLab namespace
        self.namespace = "cincan"
        # Docker Hub repository
        self.prefix = "cincan/"
        # GitLab repository
        self.project = "tools"
