from urllib.parse import quote_plus, urlparse
from typing import List
import requests
import logging


class GitLabAPI:

    """
    Simple implementation of client for GitLab API. Customized for needs of this application.

    As 29.04.2020, it should be noted that GitLab API allows 600 requests per minute.
    """

    def __init__(
        self,
        token: str = "",
        namespace: str = "",
        project: str = "",
        uri: str = "",
        timeout: int = 20,
        pool_maxsize: int = 100,
    ):
        self.logger = logging.getLogger("gitlab-api")
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=pool_maxsize)
        self.session.mount("https://", adapter)
        self.token = token
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})
        # If some uri is provided, except it to be self hosted location
        self.uri = uri
        # Some multi inheritance is applied, which are also using self.uri attr
        if self.uri:
            netloc = urlparse(self.uri).netloc
            self.api = f"https://{netloc}/api/v4/projects"
        else:
            self.api = "https://gitlab.com/api/v4/projects"
        self.namespace = namespace
        self.project = project
        self.namespace = self.namespace.strip("/")
        self.project = self.project.strip("/")

        if self.namespace and self.project:
            self.id = quote_plus(f"{self.namespace}/{self.project}")
        elif self.namespace or self.project:
            self.id = quote_plus(self.project if self.project else self.namespace)
        else:
            raise ValueError("Missing namespace or project for GitLab API")

        self.timeout = timeout

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
            self.logger.error("Rate limit reached. Starting throttling")
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
            self.logger.debug(
                f"Error on GitLab request ({self.namespace}/{self.project}): {r.status_code} : {r.json().get('message')}"
            )
            return False

    def get_full_tree(
        self,
        path: str = "",
        ref: str = "master",
        recursive: bool = False,
        page: int = 1,
        per_page: int = 20,
    ):
        contents = []
        r = self._get_tree(path, ref, recursive, page, per_page)
        if self.successful_response(r):
            contents = contents + r.json()
            while r.headers.get("X-Next-Page"):
                # print(r.headers.get("Link"))
                urls = requests.utils.parse_header_links(
                    r.headers["Link"].rstrip(">").replace(">,<", ",<")
                )
                r = None
                for url in urls:
                    if url.get("rel") == "next":
                        r = self.session.get(url.get("url"))
                        break
                if r is None:
                    raise ValueError(
                        f"Invalid urls in response headers in GitLab API: {urls}"
                    )
                if self.successful_response(r):
                    contents = contents + r.json()
                else:
                    self.logger.debug(
                        "Invalid response when following next page url in GitLab API."
                    )
                    break
        return contents

    def _get_tree(
        self,
        path: str = "",
        ref: str = "master",
        recursive: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> requests.Response:
        """ 
        Listing repository tree: https://docs.gitlab.com/ee/api/repositories.html
        """

        params = {}
        if path:
            params["path"] = quote_plus(path)
        if ref:
            params["ref"] = quote_plus(ref)
        if recursive:
            params["recursive"] = recursive
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page

        r = self.session.get(
            f"{self.api}/{self.id}/repository/tree",
            params=(params or None),
            timeout=self.timeout,
        )
        self.successful_response(r)
        return r

    def get_file_by_path(self, path: str, ref: str = "master") -> dict:
        """
        Getting files by path: https://docs.gitlab.com/ee/api/repository_files.html
        """

        params = {"ref": quote_plus(ref)}

        path = quote_plus(path)
        r = self.session.get(
            f"{self.api}/{self.id}/repository/files/{path}",
            params=params,
            timeout=self.timeout,
        )
        if self.successful_response(r):
            return r.json()
        else:
            return {}

    def get_tags(self, order_by: str = "", sort: str = "", search: str = "") -> List:
        """
        List tags of repository: https://docs.gitlab.com/ee/api/tags.html
        """
        params = {}
        if order_by:
            params["order_by"] = quote_plus(order_by)
        if sort:
            params["sort"] = quote_plus(sort)
        if search:
            params["search"] = quote_plus(search)
        r = self.session.get(
            f"{self.api}/{self.id}/repository/tags",
            params=(params or None),
            timeout=self.timeout,
        )
        if self.successful_response(r):
            return r.json()
        else:
            return []

    def get_releases(self) -> List:
        """
        List releases of repository: https://docs.gitlab.com/ee/api/releases/
        """
        r = self.session.get(f"{self.api}/{self.id}/releases", timeout=self.timeout)

        if self.successful_response(r):
            return r.json()
        else:
            return []
