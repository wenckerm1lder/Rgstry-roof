from .registry import ToolRegistry
from .toolinfo import VersionInfo
import argparse
import sys
import logging
import asyncio
import pathlib
from typing import List
import json

# from .checkers._checker import _sort_latest_tag
DEFAULT_IMAGE_FILTER_TAG = "latest-stable"

PRE_SPACE = 5
# Name length
MAX_WN = 35
# Version length # Hash can be 40 characters wide
MAX_WV = 41
# Version length with provider
MAX_WVP = 61
# Tag(s) length
MAX_WT = 20
EXTRA_FILL = 35


class color:
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    GRAY = "\033[37m"
    RED = "\033[31m"
    BOLD_RED = "\033[1m\033[31m"
    BOLD = "\033[1m"
    BOLD_YELLOW = "\033[1m\033[33m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_single_tool_version_check(tool):
    print(
        f"Name: {tool.get('name')}\nLocal version: {tool.get('local_version')}\nRemote version: {tool.get('remote_version')}\nOrigin Version: {tool.get('origin_version')}"
    )
    for other in tool.get("other_versions"):
        print(f"{other.get('provider')} version: {other.get('version')}")

    print("\nUse -j flag to print as JSON with additional details.\n")


def print_version_check(tools, only_local=True):

    print(
        f"\n{' ':<{PRE_SPACE}}{color.BOLD}  {'Tool name':<{MAX_WN}}{f'Local Version':{MAX_WV}}{f'Docker Registry Version':{MAX_WV}}{f'Origin Version':{MAX_WV}}{f'Origin Provider':{MAX_WVP}}{color.END}\n"
    )

    for tool_name in sorted(tools):

        coloring = color.GREEN

        tool = tools[tool_name]

        if tool.get("updates").get("local"):
            coloring = color.BOLD_RED
        elif tool.get("updates").get("remote"):
            coloring = color.GRAY
        if only_local:
            if not tool.get("local_version"):
                continue
        print(
            f"{coloring}{' ':<{PRE_SPACE}}| {tool_name:<{MAX_WN}}{tool.get('local_version'):{MAX_WV}}{tool.get('remote_version'):<{MAX_WV}}{tool.get('origin_version'):<{MAX_WV}}{tool.get('origin_details').get('provider') if tool.get('origin_details') else '':<{MAX_WVP}}{color.END if coloring else None}"
        )


def print_tools_by_location(tools: List[dict], location: str, filter_by: str = ""):

    # if local_tools:
    print(
        f"\n{' ':<{PRE_SPACE}}{color.BOLD}  {'Tool name':<{MAX_WN}}  {f'{location.capitalize()} Version':{MAX_WV}}  {f'{location.capitalize()} Tags':<{MAX_WT}}{color.END}\n"
    )
    if not filter_by:
        print(f"{' ':<{PRE_SPACE}}{'':-<{MAX_WN + MAX_WT + MAX_WV + EXTRA_FILL}}")
    for tool in sorted(tools):
        # print(1)
        lst = tools[tool]
        first_print = True
        if lst.versions and len(lst.versions) == 1:
            tags = ",".join(next(iter(lst.versions)).tags)
            version = next(iter(lst.versions)).version
            name = lst.name.split(":")[0]
            if filter_by and filter_by not in tags:
                continue
            print(
                f"{' ':<{PRE_SPACE}}| {name:<{MAX_WN}}| {version:{MAX_WV}}| {tags:<{MAX_WT}}"
            )
            first_print = False
        else:
            tags = ""
            version = ""
            for i, ver in enumerate(lst.versions):
                name = lst.name.split(":")[0] if first_print else ""
                # print(ver.tags)
                tags = ",".join(lst.versions[i].tags)
                version = ver.version
                if filter_by and filter_by not in tags:
                    continue
                print(
                    f"{' ':<{PRE_SPACE}}| {name:<{MAX_WN}}| {version:{MAX_WV}}| {tags:<{MAX_WT}}"
                )
                first_print = False

        if lst.versions and not first_print and not filter_by:
            print(f"{' ':<{PRE_SPACE}}{'':-<{MAX_WN + MAX_WT + MAX_WV + EXTRA_FILL}}")


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
    list_parser.add_argument(
        "-j", "--json", action="store_true", help="Print output in JSON format."
    )
    update_parser = subparsers.add_parser(
        "update", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # update_parser.add_argument(
    #     "-t", "--tool", help="Check single tool.",
    # )
    subsubparsers = list_parser.add_subparsers(dest="list_sub_command")
    local_parser = subsubparsers.add_parser(
        "local",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="List only local 'cincan' tools.",
    )
    remote_parser = subsubparsers.add_parser(
        "remote",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="List remote 'cincan' tools from registry.",
    )
    version_parser = subsubparsers.add_parser(
        "versions",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="List all versions of the tools.",
    )
    version_parser.add_argument(
        "-t", "--tool", help="Check single tool.",
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

        reg = ToolRegistry()
        format_str = "{0:<30}"
        if args.with_tags:
            format_str += " {5:<30}"
        format_str += " {1:<10}"
        format_str += " {2}"
        # print(f"Tag is {args.tag}")

        if args.list_sub_command == "local" or args.list_sub_command == "remote":

            loop = asyncio.get_event_loop()
            try:
                if args.list_sub_command == "local":
                    tools = loop.run_until_complete(
                        reg.list_tools_local_images(
                            defined_tag=args.tag if not args.all else ""
                        )
                    )
                elif args.list_sub_command == "remote":
                    tools = loop.run_until_complete(
                        reg.list_tools_registry(
                            defined_tag=args.tag if not args.all else ""
                        )
                    )

            finally:
                loop.close()
            if tools:
                if not args.all and not args.json:
                    print(f"\n  Listing all tools with tag '{args.tag}':\n")
                elif not args.all and args.json:
                    raise NotImplementedError
                    print(json.dumps(tools))
                else:
                    print(f"\n  Listing all tools :\n")

                print_tools_by_location(
                    tools, args.list_sub_command, args.tag if not args.all else ""
                )

        elif args.list_sub_command == "versions":
            loop = asyncio.get_event_loop()
            ret = loop.run_until_complete(
                reg.list_versions(
                    tool=args.tool if args.tool else "",
                    toJSON=args.json if args.json else False,
                )
            )
            if args.tool and not args.json:
                print_single_tool_version_check(ret)
            elif not args.tool and not args.json:
                print_version_check(ret)
            if args.json:
                print(ret)
            loop.close()

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
                        # lst.version,
                        lst.description,
                        ",".join(lst.input),
                        ",".join(lst.output),
                        ",".join(lst.tags),
                    )
                )

    elif sub_command == "update":
        # loop = asyncio.get_event_loop()
        # ret = loop.run_until_complete(
        #     reg.list_versions(
        #         tool=args.tool if args.tool else "",
        #         toJSON=args.json if args.json else False,
        #     )
        # )
        # for tool_name in ret:
        #     tool = ret[tool_name]
        #     if tool.


        # if not args.json:
        #     print_single_tool_version_check(ret)
        # else:
        #     print(ret)
        # loop.close()
        pass


        # print(local_tools)
        # print_local_version_check(local_tools, remote_tools, "latest-stable")
        # for tool in sorted(local_tools):
        #     tlo = local_tools[tool]
        #     print(tlo.upstream_v)
        # reg.check_upstream_versions()
        # # print(pathlib.Path.cwd())
        # for tool_path in (pathlib.Path(pathlib.Path.cwd() / "tools")).iterdir():
        #     print(tool_path.stem)
        #     print()
        # ghidra = pathlib.Path(pathlib.Path.cwd() / "tools/ghidra-decompiler/ghidra-decompiler.json")
        # checker = GithubChecker(ghidra)
        # print(checker.get_version())


if __name__ == "__main__":
    main()
