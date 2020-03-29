from ._checker import UpstreamChecker, NO_VERSION
import requests
import datetime


class GitHubChecker(UpstreamChecker):
    """
    Class for checking latests possible releases of given repository by
    release, tag release or commit.
    Uses GitHub API v3: https://developer.github.com/v3/

    Unauthenticated requests are limited to 60 per hour.
    Authenticated are limited to 5000 per hour.
    """

    def __init__(self, tool_info: dict, token: str = ""):
        """
        Please use token, which as zero scopes defined.
        It is enough to be functional and rise API limit.
        """
        super().__init__(tool_info, token)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})
        if token:
            self.session.headers.update({"Authorization": f"token {self.token}"})
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

    def _get_date_of_commit(self, sha: str) -> datetime.datetime:
        """
        Get date of commit by commit hash.
        """
        r = self.session.get(
            f"{self.api}/repos/{self.author}/{self.tool}/git/commits/{sha}"
        )
        if r.status_code != 200:
            self.logger.error(
                f"Unable to fetch date time for commit in tool {self.tool}"
            )
            raise ValueError
        return datetime.datetime.strptime(
            r.json().get("author").get("date"), "%Y-%m-%dT%H:%M:%S%z"
        )

    def _by_release(self):
        """
        Method for finding latest release from repository. Does not
        include pre-releases.
        """
        r = self.session.get(
            f"{self.api}/repos/{self.author}/{self.tool}/releases/latest"
        )
        if r.status_code == 200:
            self.version = r.json().get("tag_name", NO_VERSION)
        else:
            self._fail()

    def _by_tag(self):
        """
        Method for finding latest tag. It uses date of tagged commit for sorting.
        Consumes more API requests than other methods.
        """
        r = self.session.get(f"{self.api}/repos/{self.author}/{self.tool}/tags")
        if r.status_code == 200:
            tags = r.json()
            newest, tag_d = None, None
            for tag in tags:
                try:
                    date = self._get_date_of_commit(tag.get("commit").get("sha"))
                except ValueError:
                    self._fail()
                    return
                if not newest:
                    newest, tag_d = date, tag
                elif newest < date:
                    newest, tag_d = date, tag
            self.version = tag_d.get("name", NO_VERSION)
        else:
            self._fail()

    def _by_commit(self, current_commit: str = ""):
        """
        Get latest commit of repository in master branch.
        If comparable commit is given, it also tells how many commits
        given commit is behind master.
        """
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
