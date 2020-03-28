from ._checker import UpstreamChecker, NO_VERSION
import requests


class BitbucketChecker(UpstreamChecker):
    def __init__(self, tool_info):
        super().__init__(tool_info)
        self.session = requests.Session()
        self.api = "https://api.bitbucket.org/2.0"
        self.author = self.author.strip("/")
        self.tool = self.tool.strip("/")

    def get_version(self, curr_ver: str = ""):
        if self.method == "release":
            self._by_release()
        elif self.method == "tag-release":
            self._by_tag()
        elif self.method == "commit":
            raise NotImplementedError(f"Method {self.method} not implemented for {self.provider}")
            # self._by_commit(curr_ver)
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
            f"{self.api}/repositories/{self.author}/{self.tool}/downloads"
        )
        if r.status_code == 200:
            self.version = r.json().get("values")[0].get("name", NO_VERSION)
        else:
            self._fail()

    def _by_tag(self):
        params = {"sort":"-name"}
        r = self.session.get(f"{self.api}/repositories/{self.author}/{self.tool}/refs/tags", params=params)
        if r.status_code == 200:
            self.version = r.json().get("values")[0].get("name", NO_VERSION)
        else:
            self._fail()

    # def _by_commit(self, current_commit: str = ""):
    #     if current_commit:
    #         r = self.session.get(
    #             f"{self.api}/repositories/{self.author}/{self.tool}/compare/master...{current_commit}"
    #         )
    #         if r.status_code == 200:
    #             self.extra_info = f"{r.json().get('behind_by')} commits behind master."
    #             self.version = r.json().get("base_commit").get("sha")
    #         else:
    #             self._fail()
    #     else:
    #         r = self.session.get(
    #             f"{self.api}/repos/{self.author}/{self.tool}/commits/master"
    #         )
    #         if r.status_code == 200:
    #             self.version = r.json().get("sha")
    #             self.extra_info = "Current commit in master."
    #         else:
    #             self._fail()