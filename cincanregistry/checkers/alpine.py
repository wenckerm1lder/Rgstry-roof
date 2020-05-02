from ._checker import UpstreamChecker, NO_VERSION
import requests


class AlpineChecker(UpstreamChecker):
    """
    Class for checking latests possible tool releases of given Alpine package.
    """

    def __init__(self, tool_info: dict, **kwargs):
        super().__init__(tool_info, **kwargs)
        self.session = requests.Session()
        self.api = "https://git.alpinelinux.org/aports/plain"
        self.tool = self.tool.strip("/")
        self.repository = self.repository.strip("/")
        self.version_variable = "pkgver"

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
            f"No version information found for Alpine package {self.tool} in {self.repository} repository : {r.status_code}"
        )

    def _by_release(self):
        """
        Method for finding latest release for packages from Alpine source (git).
        """
        # Select branch
        params = {"h": self.suite}
        r = self.session.get(
            f"{self.api}/{self.repository}/{self.tool}/APKBUILD", params=params, timeout=self.timeout
        )
        # print(r.content)
        if r.status_code == 200:
            for line in r.content.splitlines():
                line = line.decode()
                if self.version_variable in line:
                    self.version = line.split("=")[1]
                    break
            if not self.version:
                self._fail(r)
        else:
            self._fail(r)
