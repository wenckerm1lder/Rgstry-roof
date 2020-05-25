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
            namespace: str = "",
            project: str = "",
            token: str = "",
    ):
        self.gl = gitlab.Gitlab('https://gitlab.com', private_token=token)
        self.logger = logging.getLogger("gitlab-util")
        self.namespace_name = namespace.strip("/")
        self.project_name = project.strip("/")

        if self.namespace_name and self.project_name:
            self.id = quote_plus(f"{self.namespace_name}/{self.project_name}")
        elif self.namespace_name or self.project_name:
            self.id = quote_plus(self.project_name if self.project_name else self.namespace_name)
        else:
            raise ValueError("Missing namespace or project for GitLab API")
        self.project = self.gl.projects.get(self.id, lazy=True)

    def get_full_tree(self, recursive=True, ref="master") -> List[dict]:
        """Get list of all files from the project repository"""
        items = self.project.repository_tree(recursive=recursive, ref=ref, all=True, per_page=100)
        return items

    def get_file_by_path(self, path: str, ref="master") -> ProjectFile:
        """Get file by path in repository"""
        file = self.project.files.get(file_path=path, ref=ref)
        return file

    def get_tags(self, order_by: str = "updated", sort: str = "", search: str = "") -> List[ProjectTag]:
        tags = self.project.tags.list(order_by=order_by, sort=sort, search=search)
        return tags

    def get_releases(self) -> List[ProjectRelease]:
        releases = self.project.releases.list()
        return releases
