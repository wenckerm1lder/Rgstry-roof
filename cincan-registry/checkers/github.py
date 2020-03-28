from ._checker import UpstreamChecker, NO_VERSION
import requests


class GithubChecker(UpstreamChecker):
    def __init__(self, path):
        super().__init__(path)
        self.session = requests.Session()
        self.api = "https://api.github.com"
        self.author = self.author.strip("/")
        self.tool = self.tool.strip("/")

    def get_version(self):
        if self.method == "release":
            self._by_release()
        elif self.method == "tag-release":
            self._by_tag()
        elif self.method == "commit":
            self._by_commit()
        return self.version

    def _by_release(self):
        r = self.session.get(
            f"{self.api}/repos/{self.author}/{self.tool}/releases/latest"
        )
        self.version = r.json().get("tag_name", NO_VERSION)

    def _by_tag(self):
        r = self.session.get(f"{self.api}/repos/{self.author}/{self.tool}/tags")
        self.version = r.json()[0].get("name", NO_VERSION)

    def _by_commit(self):
        pass
