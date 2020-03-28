from ._checker import UpstreamChecker, NO_VERSION
import requests


class GitHubChecker(UpstreamChecker):
    def __init__(self, tool_info):
        super().__init__(tool_info)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})
        self.api = "https://api.github.com"
        self.author = self.author.strip("/")
        self.tool = self.tool.strip("/")

    def get_version(self, curr_ver: str = ""):
        if self.method == "release":
            self._by_release()
        elif self.method == "tag-release":
            self._by_tag()
        elif self.method == "commit":
            self._by_commit(curr_ver)
        else:
            self.logger.error(
                f"Invalid query method for {self.provider} in tool {self.tool}."
            )
            self.version = NO_VERSION
        return self.version

    def _fail(self):
        self.version = NO_VERSION
        self.logger.error(f"Failed to fetch version update information for {self.tool}")

    def _by_release(self):
        r = self.session.get(
            f"{self.api}/repos/{self.author}/{self.tool}/releases/latest"
        )
        if r.status_code == 200:
            self.version = r.json().get("tag_name", NO_VERSION)
        else:
            self._fail()

    def _by_tag(self):
        r = self.session.get(f"{self.api}/repos/{self.author}/{self.tool}/tags")
        if r.status_code == 200:
            self.version = r.json()[0].get("name", NO_VERSION)
        else:
            self._fail()

    def _by_commit(self, current_commit: str = ""):
        if current_commit:
            r = self.session.get(
                f"{self.api}/repos/{self.author}/{self.tool}/compare/master...{current_commit}"
            )
            if r.status_code == 200:
                self.extra_info = f"{r.json().get('behind_by')} commits behind master."
                self.version = r.json().get("base_commit").get("sha")
            else:
                self._fail()
        else:
            r = self.session.get(
                f"{self.api}/repos/{self.author}/{self.tool}/commits/master"
            )
            if r.status_code == 200:
                self.version = r.json().get("sha")
                self.extra_info = "Current commit in master."
            else:
                self._fail()
