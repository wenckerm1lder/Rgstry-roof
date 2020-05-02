from ._checker import UpstreamChecker, NO_VERSION
import requests


class PypiChecker(UpstreamChecker):
    """
    Class for checking latests possible releases of given pypi package.
    """

    def __init__(self, tool_info: dict, **kwargs):
        super().__init__(tool_info, **kwargs)
        self.session = requests.Session()
        self.api = "https://pypi.org/"
        self.repository = self.repository.strip("/")
        self.tool = self.tool.strip("/")

    def _get_version(self, curr_ver: str = ""):
        if self.method == "release":
            self._by_release()
        else:
            self.logger.error(
                f"Invalid query method for {self.provider} in tool {self.tool}."
            )
            self.version = NO_VERSION

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
        Method for finding latest release from pypi.
        """
        r = self.session.get(f"{self.api}/pypi/{self.tool}/json", timeout=self.timeout)
        if r.status_code == 200:
            self.version = r.json().get("info").get("version")
        else:
            self._fail(r)
