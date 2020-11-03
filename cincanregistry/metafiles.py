import pathlib
import logging
import yaml
from os.path import basename
from datetime import timedelta, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union, List
from gitlab.exceptions import GitlabGetError

from .gitlab_utils import GitLabUtils
from .configuration import Configuration


class MetaHandler:
    """Class for fetching and caching meta files from GitLab"""

    def __init__(self,
                 config: Configuration,
                 force_refresh: bool = False
                 ):
        self.logger = logging.getLogger("metahandler")
        self.config = config
        self.force_refresh = force_refresh
        self.tool_dirs = []
        self.cincan_namespace: str = "cincan"

    def _is_old_metafile_usable(self, local_path: pathlib.Path) -> bool:

        if isinstance(local_path, pathlib.Path):
            local_path = self.config.cache_location / local_path
        else:
            raise AttributeError("Given path is not Path object.")
        if not local_path.is_file():
            self.logger.debug(
                f"No existing metafile found for {local_path.parent.stem}"
            )
            return False
        mtime = datetime.fromtimestamp(local_path.stat().st_mtime)
        now = datetime.now()
        if now - timedelta(hours=self.config.cache_lifetime) <= mtime <= now:
            self.logger.debug(
                f"Using old metafile for {local_path.parent.stem} : updated in past {self.config.cache_lifetime} hours."
            )
            return True
        else:
            self.logger.info(
                f"Outdated meta file for {local_path.parent.stem}. Updating..."
            )
            return False

    def _get_index_file(self, client: GitLabUtils) -> bytes:
        file_content = client.get_file_by_path(self.config.index_file, ref=self.config.branch).decode()
        # Cache content
        with (self.config.cache_location / self.config.index_file).open("wb") as f:
            f.write(file_content)
        return client.get_file_by_path(self.config.index_file, ref=self.config.branch).decode()

    def read_index_file(self, index_f: Union[bytes, pathlib.Path]) -> List:
        """Get index file, which tells paths for tools"""
        if isinstance(index_f, pathlib.Path):
            with index_f.open("r") as f:
                index_f = f.read()
        yaml_obj = yaml.safe_load(index_f)
        self.tool_dirs = yaml_obj.get("tools")
        return self.tool_dirs

    def cache_metafile_by_path(
            self, client: GitLabUtils, path: pathlib.Path, ref: str
    ) -> Union[pathlib.Path, None]:

        file_path = None
        if not self.force_refresh:
            if self._is_old_metafile_usable(path):
                return
        try:
            resp = client.get_file_by_path(str(path), ref=ref)
        except GitlabGetError as e:
            resp = None
        if resp:
            file_data = resp.decode()
            if str(path).count("/") > 2 or str(path).startswith("_") or not str(path).startswith(
                    tuple(self.tool_dirs)):
                self.logger.warning(
                    f"File {str(path)} in wrong place at GitLab repository, skipping..."
                )
                return
            # Path contains its location in GitLab (Stable, dev etc.), remote it
            path = pathlib.Path("/".join(path.parts[1:]))
            file_path = self.config.cache_location / path
            # Make subdirectory - should be tool name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(file_data)
                self.logger.info(f"Metafile generated into {file_path}")
        else:
            self.logger.info(f"No metafile for {path.parent} from GitLab")
        return file_path

    def get_meta_files_from_gitlab(
            self, tools: [List, str], branch: str
    ) -> bool:
        """
        Return true if new meta files
        """
        if tools:
            # Create store location directory
            self.config.cache_location.mkdir(parents=True, exist_ok=True)
        else:
            raise ValueError("Empty 'tools' attribute provided to metafiles fetch.")

        self.logger.info(
            f"Fetching meta information files from GitLab"
            f" (https://gitlab.com/{self.cincan_namespace}/{self.config.project})"
            f" into path '{self.config.cache_location}'"
        )
        gitlab_client = GitLabUtils(
            namespace=self.cincan_namespace, project=self.config.project, token=self.config.tokens.get("gitlab", "")
        )
        self.read_index_file(self._get_index_file(gitlab_client))

        # tools with 'cincan' prefix

        # NOTE slower at lower tool amounts but safer method
        # Get list of all files in repository
        # meta_tools contain only tools with meta files - no extra 404 later
        files = gitlab_client.get_full_tree(
            ref=branch
        )
        # Get paths of each meta file
        meta_paths = []
        for file in files:
            if file.get("name") == self.config.meta_filename:
                p = pathlib.Path(file.get("path"))
                if p.parent.name in tools:
                    meta_paths.append(p)

        if not meta_paths:
            self.logger.debug(f"No single meta file found from GitLab for tools: {', '.join(tools)}")
            # raise FileNotFoundError(
            #     f"No single meta file ({self.config.meta_filename})"
            #     f" found from GitLab ({self.cincan_namespace}/{self.config.project})"
            # )
            return False

        # Write and fetch each file from GitLab
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Start the load operations and mark each future with its path
            future_to_fetch = {
                executor.submit(
                    self.cache_metafile_by_path, gitlab_client, path, branch
                ): path
                for path in meta_paths
            }
            for future in as_completed(future_to_fetch):
                path = future_to_fetch[future]
                try:
                    future.result()
                except Exception as exc:
                    self.logger.error(f"{path} generated an exception: {exc}")
                else:
                    pass

            self.logger.info("Required metafiles checked.")
            return True

