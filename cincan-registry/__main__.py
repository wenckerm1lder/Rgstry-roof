from .registry import ToolRegistry
import argparse
import sys
import logging
import asyncio
import pathlib

DEFAULT_IMAGE_FILTER_TAG = "latest-stable"


class color:
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def main():

    m_parser = argparse.ArgumentParser()
    m_parser.add_argument(
        "-l",
        "--log",
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
        default=None,
    )
    m_parser.add_argument("-q", "--quiet", action="store_true", help="Be quite quiet")
    subparsers = m_parser.add_subparsers(dest="sub_command")

    list_parser = subparsers.add_parser(
        "list", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    list_exclusive_group = list_parser.add_mutually_exclusive_group()
    list_exclusive_group.add_argument(
        "-t",
        "--tag",
        default=DEFAULT_IMAGE_FILTER_TAG,
        help="Filter images by tag name.",
    )
    list_exclusive_group.add_argument(
        "-a", "--all", action="store_true", help="List all images from the registry."
    )
    list_parser.add_argument(
        "-w",
        "--with-tags",
        action="store_true",
        help="Show all tags of selected images.",
    )
    update_parser = subparsers.add_parser(
        "check-updates", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subsubparsers = list_parser.add_subparsers(dest="list_sub_command")
    list_parser = subsubparsers.add_parser(
        "local",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="List only local 'cincan' tools.",
    )
    list_parser = subsubparsers.add_parser(
        "remote",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="List remote 'cincan' tools from registry.",
    )

    if len(sys.argv) > 1:
        args = m_parser.parse_args(args=sys.argv[1:])
    else:
        args = m_parser.parse_args(args=["help"])

    sub_command = args.sub_command

    log_level = (
        args.log_level if args.log_level else ("WARNING" if args.quiet else "INFO")
    )
    if log_level not in {"DEBUG"}:
        sys.tracebacklimit = 0  # avoid track traces unless debugging
    logging.basicConfig(
        format="%(name)s: %(message)s", level=getattr(logging, log_level)
    )

    if sub_command == "help":
        m_parser.print_help()
        sys.exit(1)

    elif sub_command == "list":

        MAX_WN = 35
        MAX_WV = 15
        MAX_WT = 20

        reg = ToolRegistry()
        format_str = "{0:<30}"
        if args.with_tags:
            format_str += " {5:<30}"
        format_str += " {1:<10}"
        format_str += " {2}"
        # print(f"Tag is {args.tag}")

        if args.list_sub_command == "local":

            loop = asyncio.get_event_loop()
            try:
                local_tools = loop.run_until_complete(
                    reg.list_tools_local_images(
                        defined_tag=args.tag if not args.all else ""
                    )
                )
            finally:
                loop.close()
            if not args.all and local_tools:
                print(f"\n  Listing all tools with tag '{args.tag}':\n")

            if local_tools:
                print(
                    f"\n{color.BOLD}{f'Tool name':<{MAX_WN}}{f'Local Version':{MAX_WV}}{f'Local Tags':<{MAX_WT}}{color.END}\n"
                )
            for tool in sorted(local_tools):
                # print(1)
                lst = local_tools[tool]
                if lst.versions and len(lst.versions) == 1:
                    tags = ",".join(next(iter(lst.versions)).tags)
                    version = next(iter(lst.versions)).version
                    name = lst.name.split(":")[0]
                    print(f"{name:<{MAX_WN}}{version:{MAX_WV}}{tags:<{MAX_WT}}")
                else:
                    tags = ""
                    version = ""
                    for i, ver in enumerate(lst.versions):
                        name = lst.name.split(":")[0] if i == 0 else ""
                        # print(ver.tags)
                        tags = ",".join(lst.versions[i].tags)
                        version = ver.version
                        print(f"{name:<{MAX_WN}}{version:{MAX_WV}}{tags:<{MAX_WT}}")

        # elif args.list_sub_command == "remote":
        else:
            # tools_list = reg.list_tools(defined_tag=args.tag if not args.all else "")

            try:
                tool_list = reg.list_tools(defined_tag=args.tag if not args.all else "")
            except OSError:
                print(f"Failed to connect to Docker.")
            if not args.all and tool_list:
                print(f"\n  Listing all tools with tag '{args.tag}':\n")
            for tool in sorted(tool_list):
                lst = tool_list[tool]

                # print(lst.version)
                # print(format_str)
                print(
                    format_str.format(
                        lst.name.split(":")[0],
                        lst.version,
                        lst.description,
                        ",".join(lst.input),
                        ",".join(lst.output),
                        ",".join(lst.tags),
                    )
                )

    elif sub_command == "check-updates":
        # from .checkers.github import GithubChecker
        reg = ToolRegistry()
        reg.check_upstream_versions()
        # # print(pathlib.Path.cwd())
        # for tool_path in (pathlib.Path(pathlib.Path.cwd() / "tools")).iterdir():
        #     print(tool_path.stem)
        #     print()
        # ghidra = pathlib.Path(pathlib.Path.cwd() / "tools/ghidra-decompiler/ghidra-decompiler.json")
        # checker = GithubChecker(ghidra)
        # print(checker.get_version())


if __name__ == "__main__":
    main()
