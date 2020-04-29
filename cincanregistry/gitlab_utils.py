from urllib.parse import quote_plus, urlparse
from typing import List, Union
import requests
import logging


class GitLabAPI:

    """
    Simple implementation of client for GitLab API. Customized for needs of this application.

    As 29.04.2020, it should be noted that GitLab API allows 600 requests per minute.
    """

    def __init__(self, token: str = "", namespace: str = "", project: str = ""):
        self.logger = logging.getLogger("gitlab-api")
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {self.token}"})
        if self.uri:
            netloc = urlparse(self.uri).netloc
            self.api = f"https://{netloc}/api/v4/projects"
        else:
            self.api = "https://gitlab.com/api/v4/projects"
        if namespace:
            self.namespace = namespace
        if project:
            self.project = project
        self.namespace = self.namespace.strip("/")
        self.project = self.project.strip("/")

        if self.namespace and self.project:
            self.id = quote_plus(f"{self.namespace}/{self.project}")
        else:
            self.id = quote_plus(self.tool if self.tool else self.repository)

    def _check_rate_limit(self, r: requests.Response):

        # Ratelimits might not be applied on self-hosted instances
        remaining = (
            int(r.headers.get("RateLimit-Remaining"))
            if r.headers.get("RateLimit-Remaining")
            else None
        )
        if remaining is None:
            self.logger.debug(f"Rate limit not implemented for {r.url}")
            return
        if remaining == 0:
            self.logger("Rate limit reached. Starting throttling")
            # TODO ratelimit throttle
        elif remaining < 10:
            self.logger.warning("Less than 10 requests remaining for GitLab API")
            self.logger.warning(
                f"Rate limit resets at: {r.headers.get('RateLimit-ResetTime')}"
            )
            self.logger.warning(
                f"Maximum requests are {r.headers.get('RateLimit-Limit')}"
            )

        else:
            return

    def successful_response(self, r: requests.Response) -> bool:
        self._check_rate_limit(r)
        if r.status_code == 200:
            return True
        else:
            self.logger.error(
                f"Error on GitLab request ({self.namespace}/{self.project}): {r.status_code} : {r.json().get('message')}"
            )
            return False

    def get_file_by_path(self, path: str) -> requests.Response:

        path = quote_plus(path)
        r = f"{self.api}/projects/{self.id}/repository/files/{path}"
        if self.successful_response(r):
            return r
        # self.session.get()

    def get_tags(
        self, order_by: str = "", sort: str = "", search: str = ""
    ) -> Union[dict, List]:

        params = {}
        if order_by:
            params["order_by"] = order_by
        if sort:
            params["sort"] = sort
        if search:
            params["search"] = search
        r = self.session.get(
            f"{self.api}/{self.id}/repository/tags",
            params=(params or None),
            timeout=self.timeout,
        )
        if self.successful_response(r):
            return r.json()
        else:
            return {}

    def get_releases(self) -> Union[dict, List]:

        r = self.session.get(f"{self.api}/{self.id}/releases", timeout=self.timeout)

        if self.successful_response(r):
            return r.json()
        else:
            return {}
