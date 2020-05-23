from cincanregistry import HubReadmeHandler


def test_update_tool_readme(mocker, tmpdir):
    p = tmpdir.mkdir("my_tool").join("README.md")
    p.write("# This is useful example tool.")
    reg = HubReadmeHandler()
    mocker.patch.object(
        reg.client, "ping", return_value=True, autospec=True,
    )
    # print(reg._is_docker_running())