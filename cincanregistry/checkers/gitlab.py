from ._checker import UpstreamChecker, NO_VERSION
from ..gitlab_utils import GitLabUtils
from gitlab.exceptions import GitlabError


class GitLabChecker(UpstreamChecker, GitLabUtils):
    """
    Class for checking latest possible releases of given repository by
    release or tag release.
    Uses GitLab API v4: https://docs.gitlab.com/ee/api/
    """

    def __init__(self, tool_info: dict, **kwargs):
        """
        Please use token, with zero scopes defined!
        It is enough to be functional and rise API limit.
        """
        UpstreamChecker.__init__(self, tool_info=tool_info, **kwargs)
        GitLabUtils.__init__(
            self,
            url=self.uri,
            namespace=self.repository,
            project=self.tool,
            token=kwargs.get("token", "")
        )

    def _get_version(self, curr_ver: str = ""):
        if self.method == "release":
            self._by_release()
        elif self.method == "tag-release":
            self._by_tag()
        else:
            self.logger.error(
                f"Invalid query method for {self.provider} in tool {self.project}."
            )
            self.version = NO_VERSION

    def _fail(self, r=None, e: GitlabError = None):
        """
        Set version for not defined on fail, log error.
        """
        self.version = NO_VERSION
        self.logger.error(
            f"Failed to fetch version update information for {self.project}: {e}"
        )

    def _by_release(self):
        """
        Method for finding latest release from repository.
        """
        try:
            r = self.get_releases()
            if r:
                self.version = r[0].name
            else:
                self.logger.debug(f"No releases found for {self.project} with {self.provider}")
        except GitlabError as e:
            self._fail(e=e)

    def _by_tag(self):
        """
        Method for finding latest tag.
        """
        try:
            r = self.get_tags()
            if r:
                self.version = r[0].name
            else:
                self.logger.debug(f"No tags found for {self.project} with {self.provider}")
        except GitlabError as e:
            self._fail(e=e)


'''
    def _by_commit(self, current_commit: str = ""):
        """
        Get latest commit of repository in master branch.
        If comparable commit is given, it also tells how many commits
        given commit is behind master.
        """
        if current_commit:
            r = self.session.get(
                f"{self.api}/{self.author}%2F{self.project}/repository/compare/master?from=master&to{current_commit}
            )
            if r.status_code == 200:
                self.extra_info = f"{r.json().get('behind_by')} commits behind master."
                self.version = r.json().get("base_commit").get("sha")
            else:
                self._fail(r)
        else:
            r = self.session.get(
                f"{self.api}/{self.author}%2F{self.project}/repository/commits/master"
            )
            if r.status_code == 200:
                self.version = r.json().get("sha")
                self.extra_info = "Current commit in master."
            else:
                self._fail(r)


    def _get_date_of_commit(self, sha: str) -> datetime.datetime:
        """
        Get date of commit by commit hash.
        """
        r = self.session.get(
            f"{self.api}/{self.author}%2F{self.project}/repository/tags"
        )
        if r.status_code != 200:
            self.logger.error(
                f"Unable to fetch date time for commit in tool {self.tool}: {r.json().get('message')}"
            )
            raise ValueError
        return datetime.datetime.strptime(
            r.json()[0].get("commit").get("committed_date"), "%Y-%m-%dT%H:%M:%S.%f%z"
        )
'''
