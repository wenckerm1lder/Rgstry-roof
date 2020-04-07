from ._checker import UpstreamChecker, NO_VERSION
import requests


class DebianChecker(UpstreamChecker):
    """
    Class for checking latests possible tool releases of given debian package.
    """

    def __init__(self, tool_info: dict, token: str = ""):
        super().__init__(tool_info, token)
        self.session = requests.Session()
        self.api = "https://sources.debian.org/api/src/"
        self.tool = self.tool.strip("/")

    def get_version(self, curr_ver: str = ""):
        if self.method == "release":
            self._by_release()
        else:
            self.logger.error(
                f"Invalid query method for {self.provider} in tool {self.tool}."
            )
            self.version = NO_VERSION
        return self.version

    def _fail(self, r: requests.Response):
        """
        Set version for not defined on fail, log error.
        """
        self.version = NO_VERSION
        self.logger.error(
            f"Failed to fetch version update information for {self.tool}: {r.status_code} : {r.json().get('message')}"
        )

    def _by_release(self):
        """
        Method for finding latest release from debian sources.
        """
        r = self.session.get(f"{self.api}/{self.tool}")
        if r.status_code == 200:
            data = r.json().get("versions")
            #loop trough version list and get wanted version. 
            #Wanted version is defined in spesific tool json
            for x in data:
                for y in x["suites"]:
                    if y == self.suite:
                        self.version=x["version"]
        else:
            self._fail(r)
