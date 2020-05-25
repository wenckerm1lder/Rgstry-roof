from gitlab.v4.objects import ProjectFile
from cincanregistry.gitlab_utils import GitLabUtils
from .fake_instances import GITLAB_FAKE_META_DICT
from unittest import mock


def test_create_instance():
    gl_util = GitLabUtils(namespace="cincan", project="tools", token="12345")
    assert gl_util.namespace_name == "cincan"
    assert gl_util.project_name == "tools"
    assert gl_util.gl.url == "https://gitlab.com"
    assert gl_util.gl.private_token == "12345"
    assert gl_util.project._attrs == {'id': 'cincan%2Ftools'}


def test_get_file_by_path(mocker):
    gl_util = GitLabUtils(namespace="cincan", project="tools")
    resp = mock.Mock(spec=ProjectFile)
    resp.file_name = GITLAB_FAKE_META_DICT.get("file_name")
    resp.file_path = GITLAB_FAKE_META_DICT.get("file_path")
    resp.content = GITLAB_FAKE_META_DICT.get("content")

    mocker.patch.object(gl_util.project.files, "get", return_value=resp)
    file = gl_util.get_file_by_path("radare2/meta.json")
    gl_util.project.files.get.assert_called_with(file_path="radare2/meta.json", ref="master")
    assert file.file_name == GITLAB_FAKE_META_DICT.get("file_name")
    assert file.file_path == GITLAB_FAKE_META_DICT.get("file_path")
    assert file.content == GITLAB_FAKE_META_DICT.get("content")


def test_get_full_tree(mocker):
    gl_util = GitLabUtils(namespace="cincan", project="tools")
    fake_tree = mock.Mock()
    fake_tree.return_value = True
    m = mocker.patch.object(gl_util, "project")
    m().repository_tree = fake_tree
    gl_util.get_full_tree(ref="development")
    m.repository_tree.assert_called_with(recursive=True, ref="development", all=True, per_page=100)


def test_get_tags(mocker):
    gl_util = GitLabUtils(namespace="cincan", project="tools")
    fake_tags = mock.Mock()
    fake_tags.return_value = [{"Many tags"}]
    m = mocker.patch.object(gl_util.project.tags, "list", fake_tags)
    assert gl_util.get_tags() == [{"Many tags"}]
    gl_util.project.tags.list.assert_called_with(order_by="updated", sort="desc", search="")


def test_get_releases(mocker):
    gl_util = GitLabUtils(namespace="cincan", project="tools")
    fake_releases = mock.Mock()
    fake_releases.return_value = [{"Many releases"}]
    m = mocker.patch.object(gl_util.project.releases, "list", fake_releases)
    assert gl_util.get_releases() == [{"Many releases"}]
    gl_util.project.releases.list.assert_called_with()
