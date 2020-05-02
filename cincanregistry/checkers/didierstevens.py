from ._checker import NO_VERSION
from .github import GitHubChecker
import base64


class DidierStevensChecker(GitHubChecker):
    """
    Class for checking latests possible tool releases of Didier Stevens.
    """

    def __init__(self, tool_info: dict, **kwargs):
        super().__init__(tool_info, **kwargs)
        self.version_variable = "__version__"

    def _get_version(self, curr_ver: str = ""):
        if self.method == "release":
            self._by_release()
        else:
            self.logger.error(
                f"Invalid query method for {self.provider} in tool {self.tool}."
            )
            self.version = NO_VERSION

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
        if r.status_code == 200:
            encoded_file = resp.get("content")
            decoded = base64.b64decode(encoded_file)
            for line in decoded.splitlines():
                line = line.decode()
                if self.version_variable in line:
                    self.version = line.split("=")[1].strip()
                    break
            if not self.version:
                self._fail(r)
        else:
            self._fail(r)
