from ._checker import UpstreamChecker, NO_VERSION
import requests
import base64


class DidierStevensChecker(UpstreamChecker):
    """
    Class for checking latests possible tool releases of Didier Stevens.
    """

    def __init__(self, tool_info: dict, token: str = ""):
        super().__init__(tool_info, token)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})
        if token:
            self.session.headers.update({"Authorization": f"token {self.token}"})
        self.api = "https://api.github.com"
        self.repository = self.repository.strip("/")
        self.tool = self.tool.strip("/")
        self.version_variable = "__version__"

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
        Method for finding latest release for single tool from DidierStevens Git repository.
        """
        # Select branch
        r = self.session.get(
            f"{self.api}/repos/{self.repository}/{self.suite}/contents/{self.tool}.py",
            timeout=self.timeout,
        )
        resp = r.json()
        encoded_file = resp.get("content")
        decoded = base64.b64decode(encoded_file)
        # print(r.content)
        if r.status_code == 200:
            for line in decoded.splitlines():
                line = line.decode()
                if self.version_variable in line:
                    self.version = line.split("=")[1].strip()
                    break
            if not self.version:
                self._fail(r)
        else:
            self._fail(r)
