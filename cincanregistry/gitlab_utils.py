from urllib.parse import quote_plus, urlparse
from typing import List
import requests
import logging
import gitlab
from gitlab.v4.objects import ProjectFile, ProjectRelease, ProjectTag


class GitLabUtils:
    """ Wrapper for GitLab API """

    def __init__(
            self,
            url: str = "",
            namespace: str = "",
            project: str = "",
            token: str = "",
            pool_maxsize: int = 100
    ):
        if url:
            url = f"https://{urlparse(url).netloc}/"
        self.base_url = url or "https://gitlab.com"
        self.gl = gitlab.Gitlab(self.base_url, private_token=token)
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=pool_maxsize)
        self.gl.session.mount("https://", adapter)
        self.logger = logging.getLogger("gitlab-util")
        self.namespace_name = namespace.strip("/")
        self.project_name = project.strip("/")

        if self.namespace_name and self.project_name:
            self.id = f"{self.namespace_name}/{self.project_name}"
        elif self.namespace_name or self.project_name:
            self.id = self.project_name if self.project_name else self.namespace_name
        else:
            raise ValueError("Missing namespace or project name for GitLab API")
        self.project = self.gl.projects.get(self.id, lazy=True)

    def get_full_tree(self, recursive=True, ref="master") -> List[dict]:
        """Get list of all files from the project repository"""
        items = self.project.repository_tree(recursive=recursive, ref=ref, all=True, per_page=100)
        return items

    def get_file_by_path(self, path: str, ref="master") -> ProjectFile:
        """Get file by path in repository"""
        file = self.project.files.get(file_path=path, ref=ref)
        return file

    def get_tags(self, order_by: str = "updated", sort: str = "desc", search: str = "") -> List[ProjectTag]:
        """Get tags of project"""
        tags = self.project.tags.list(order_by=order_by, sort=sort, search=search)
        return tags

    def get_releases(self) -> List[ProjectRelease]:
        """Get releases of project"""
        releases = self.project.releases.list()
        return releases
