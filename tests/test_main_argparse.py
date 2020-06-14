from cincanregistry import create_list_argparse
import argparse
import pytest
DEFAULT_TAG = "latest"


def test_create_list_argparse(caplog, capsys):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="sub_command")
    create_list_argparse(subparsers)
    test_args = ["list"]
    args = parser.parse_args(test_args)
    assert not args.local
    assert not args.remote
    assert not args.all
    assert not args.json
    assert not args.size
    assert args.tag == DEFAULT_TAG
    assert not args.config

    test_args = ["list", "-ja"]
    args = parser.parse_args(test_args)
    assert not args.local
    assert not args.remote
    assert args.all
    assert args.json
    assert not args.size
    assert args.tag == DEFAULT_TAG
    assert not args.config

    test_args = ["list", "-lr"]
    with pytest.raises(SystemExit) as ex:
        args = parser.parse_args(test_args)
    assert ex.type == SystemExit
    assert ex.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.endswith("list: error: argument -r/--remote: not allowed with argument -l/--local\n")

    test_args = ["list", "-at"]
    with pytest.raises(SystemExit) as ex:
        args = parser.parse_args(test_args)
    assert ex.type == SystemExit
    assert ex.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.endswith("list: error: argument -t/--tag: expected one argument\n")

    test_args = ["list", "-j", "-r"]
    args = parser.parse_args(test_args)
    assert not args.local
    assert args.remote
    assert not args.all
    assert args.json
    assert not args.size
    assert args.tag == DEFAULT_TAG
    assert not args.config

    test_args = ["list", "-j", "-l"]
    args = parser.parse_args(test_args)
    assert args.local
    assert not args.remote
    assert not args.all
    assert args.json
    assert not args.size
    assert args.tag == DEFAULT_TAG
    assert not args.config

    test_args = ["list", "-t", "dev"]
    args = parser.parse_args(test_args)
    assert not args.local
    assert not args.remote
    assert not args.all
    assert not args.json
    assert not args.size
    assert args.tag == "dev"
    assert not args.config


def test_create_list_version_argparse(caplog, capsys):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="sub_command")
    create_list_argparse(subparsers)
    test_args = ["list", "versions"]
    args = parser.parse_args(test_args)
    assert args.list_sub_command == "versions"
    assert not args.local
    assert not args.remote
    assert not args.all
    assert not args.json
    assert not args.size
    assert args.tag == "latest"
    assert not args.config
    assert not args.only_updates
    assert not args.with_tags
    assert not args.name
    assert not args.force_refresh

    test_args = ["list", "versions", "-u", "-n test"]
    with pytest.raises(SystemExit) as ex:
        args = parser.parse_args(test_args)
    assert ex.type == SystemExit
    assert ex.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.endswith("error: argument -n/--name: not allowed with argument -u/--only-updates\n")

    test_args = ["list", "versions", "-n"]
    with pytest.raises(SystemExit) as ex:
        args = parser.parse_args(test_args)
    assert ex.type == SystemExit
    assert ex.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.endswith("argument -n/--name: expected one argument\n")

    test_args = ["list", "-r", "versions", "-uf"]
    args = parser.parse_args(test_args)
    assert not args.local
    assert args.remote
    assert not args.all
    assert not args.json
    assert not args.size
    assert args.tag == DEFAULT_TAG
    assert args.only_updates
    assert args.force_refresh

    test_args = ["list", "versions", "-n", "cincan/test"]
    args = parser.parse_args(test_args)
    assert args.name == "cincan/test"

    test_args = ["list", "versions", "-fwn", "cincan/test"]
    args = parser.parse_args(test_args)
    assert not args.local
    assert not args.remote
    assert not args.all
    assert not args.json
    assert not args.size
    assert args.tag == DEFAULT_TAG
    assert not args.only_updates
    assert args.force_refresh
    assert args.with_tags
    assert args.name == "cincan/test"
