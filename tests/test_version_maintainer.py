from cincanregistry.gitlab_utils import GitLabUtils
from cincanregistry.version_maintainer import VersionMaintainer
from cincanregistry.configuration import Configuration
import pathlib


def test_cache_metafile_by_path():
    path = pathlib.Path("testt/meta.json")
    gl_client = GitLabUtils(namespace="cincan", project="tools")
    # ver_man = VersionMaintainer(config)
