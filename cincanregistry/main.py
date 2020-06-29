from . import ToolRegistry, ToolInfoEncoder, HubReadmeHandler, ToolInfo
import argparse
import sys
import logging
import asyncio
import json
from typing import Dict

DEFAULT_IMAGE_FILTER_TAG = "latest"

PRE_SPACE = 0
# Name length
MAX_WN = 35
# Size width
MAX_WS = 10

# Base version length, showing only first 8 chars.
# Hash can be 40 chars long
CHARS_TO_SHOW = 20
# Version Length
MAX_WV = CHARS_TO_SHOW + 1
# Provider length
MAX_WP = 15
# Version length with provider
MAX_WVP = MAX_WV + MAX_WP

# Tag(s) length
MAX_WT = 20
# Description length
MAX_WD = 30

EXTRA_FILL = 35


class color:
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    GREEN_BACKGROUND = "\033[102m"
    YELLOW = "\033[93m"
    GRAY = "\033[90m"
    GRAY_BACKGROUND = "\033[100m"
    RED = "\033[31m"
    RED_BACKGROUND = "\033[41m"
    BOLD_RED = "\033[1m\033[31m"
    BOLD = "\033[1m"
    BOLD_YELLOW = "\033[1m\033[33m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_single_tool_version_check(tool, show_tags: bool = False):
    # Provider name length
    MAX_WN = 25
    MAX_WV = 40
    print(f"\n{' ':<{PRE_SPACE}}{color.GREEN}  {tool.get('name')}{color.END}")
    # pre-space and text format
    print(f"\n{' ':<{PRE_SPACE}}", end="")
    # Location
    underlined_loc = f"{color.UNDERLINE}Location{color.END}"
    underlined_ver = f"{color.UNDERLINE}Version{color.END}"
    underlined_tags = f"{color.UNDERLINE}Tags{color.END}"
    # Underline "eats" padding by adding extra chars
    print(f"  {underlined_loc:<{MAX_WN + 8}}", end="")
    print(f"{underlined_ver:<{MAX_WV + 8}}", end="")
    if show_tags:
        print(f"{underlined_tags:<{MAX_WT}}", end="")
    print()
    print()
    # local
    if tool.get("versions").get("local"):
        local = tool.get("versions").get("local")
        print(f"{' ':<{PRE_SPACE}}", end="")
        print(f"| {'Local':<{MAX_WN}}", end="")
        print(f"{local.get('version'):<{MAX_WV}}", end="")
        if show_tags:
            print(f"{','.join(local.get('tags')):<{MAX_WT}}", end="")
        print()
    # remote
    if tool.get("versions").get("remote"):
        remote = tool.get("versions").get("remote")
        print(f"{' ':<{PRE_SPACE}}", end="")
        print(f"| {'Remote':<{MAX_WN}}", end="")
        print(f"{remote.get('version'):<{MAX_WV}}", end="")
        if show_tags:
            print(f"{','.join(remote.get('tags')):<{MAX_WT}}", end="")
        print()
    # other
    if tool.get("versions").get("origin"):
        print(
            f"{' ':<{PRE_SPACE}}| {tool.get('versions').get('origin').get('details').get('provider'):<{MAX_WN}}",
            end="",
        )
        print(f"{tool.get('versions').get('origin').get('version'):<{MAX_WV}}")

    if tool.get("versions").get("other"):
        for other in tool.get("versions").get("other"):
            print(
                f"{' ':<{PRE_SPACE}}| {other.get('details').get('provider'):<{MAX_WN}}",
                end="",
            )
            print(f"{other.get('version'):<{MAX_WV}}")

    print("\n  Use -j flag to print as JSON with additional details.\n")


def print_version_check(
        tools: dict, location="both", only_updates: bool = False, show_tags: bool = False
):
    # TODO add maybe tag column somehow

    print(f"\n{' ':<{PRE_SPACE}}Color explanations:", end=" ")
    print(f"{color.GREEN_BACKGROUND}  {color.END} - tool up to date", end=" ")
    print(f"{color.RED_BACKGROUND}  {color.END} - update available in remote", end=" ")
    print(f"{color.GRAY_BACKGROUND}  {color.END} - remote differs from tool origin")

    if location == "local":
        print(
            f"\n{' ':<{PRE_SPACE}}By default, only versions for available local tools are visible."
        )
    print(
        f"\n{' ':<{PRE_SPACE}}Only first {CHARS_TO_SHOW} characters are showed from version."
    )
    print(
        f"\n{' ':<{PRE_SPACE}}(*) means, that origin provider is Dockerfile installation origin, not tool origin."
    )

    # pre-space and text format
    print(f"\n{' ':<{PRE_SPACE}}{color.BOLD}  ", end="")
    # name
    print(f"{'Tool name':<{MAX_WN}}", end="")
    # local ver
    print(f"{f'Local Version':{MAX_WV}}", end="")
    # registry ver
    print(f"{f'DockerHub Version':{MAX_WV}}", end="")
    # origin ver
    print(f"{f'Origin Version':{MAX_WV}}", end="")
    # origin provider
    print(f"{f'Origin Provider':{MAX_WP}}", end="")

    # end text format
    print(f"{color.END}\n")

    for tool_name in sorted(tools):

        coloring = color.GREEN

        tool = tools[tool_name]

        if tool.get("updates").get("local") and location in ["local", "both"]:
            coloring = color.BOLD_RED
        elif tool.get("updates").get("remote"):
            coloring = color.GRAY
        if location == "local":
            if not tool.get("versions").get("local"):
                continue
            if not tool.get("versions").get("local").get("version"):
                continue
        if location == "remote" and only_updates:
            if not tool.get("updates").get("remote"):
                continue

        # pre-space and color
        print(f"{coloring}{' ':<{PRE_SPACE}}| ", end="")
        # name
        print(f"{tool_name:<{MAX_WN}}", end="")
        # local version
        versions = tool.get("versions")
        l_ver = versions.get("local").get("version") if versions.get("local") else ""
        print(
            f"{l_ver[:CHARS_TO_SHOW]:{MAX_WV}}", end="",
        )
        # remote version
        r_ver = versions.get("remote").get("version") if versions.get("remote") else ""

        print(
            f"{r_ver[:CHARS_TO_SHOW]:<{MAX_WV}}", end="",
        )

        # --- origin check ---
        org_details = versions.get("origin").get("details")
        if (
                org_details
                and not org_details.get("origin")
                and org_details.get("docker_origin")
        ):
            mark_as_not_source = "(*)"
        else:
            mark_as_not_source = ""

        # origin version
        if versions.get("origin"):
            print(
                f"{versions.get('origin').get('version')[:CHARS_TO_SHOW]:<{MAX_WV}}",
                end="",
            )
        # origin provider
        print(
            f"{(org_details.get('provider') + mark_as_not_source) if org_details else '':<{MAX_WP}}",
            end="",
        )
        # end colored section
        print(f"{color.END if coloring else None}")
    print()


def print_tools_by_location(
        tools: Dict[str, ToolInfo], location: str, filter_by: str = "", show_size=False
):
    MAX_WV = 41
    if location == "remote" and show_size:
        print(f"{' ':<{PRE_SPACE}} Size as compressed in Remote.")
    if location == "local" and show_size:
        print(f"{' ':<{PRE_SPACE}} Size as uncompressed in Local.")
    print(f"\n{' ':<{PRE_SPACE}}{color.BOLD}  ", end="")
    print(f"{'Tool name':<{MAX_WN}}  ", end="")
    print(f"{f'{location.capitalize()} Version':{MAX_WV}}  ", end="")
    if show_size:
        print(f"{'Size':<{MAX_WS}}   ", end="")
    print(f"{f'{location.capitalize()} Tags':<{MAX_WT}}", end="")
    print(f"{color.END}\n")
    # if not filter_by:
    # print(f"{' ':<{PRE_SPACE}}{'':-<{MAX_WN + MAX_WT + MAX_WV + EXTRA_FILL}}")
    for tool in sorted(tools):
        lst = tools[tool]
        first_print = True
        if lst.versions and len(lst.versions) == 1:
            tags = ",".join(next(iter(lst.versions)).tags)
            size = next(iter(lst.versions)).size
            version = next(iter(lst.versions)).version
            name = lst.name.split(":")[0]
            if filter_by and filter_by not in tags:
                continue
            print(f"{' ':<{PRE_SPACE}}| ", end="")
            print(f"{name:<{MAX_WN}}| ", end="")
            print(f"{version:{MAX_WV}}| ", end="")
            if show_size:
                print(f"{size:>{MAX_WS}} | ", end="")
            print(f"{tags:<{MAX_WT}}")
        else:
            if not filter_by:
                print(
                    f"{' ':<{PRE_SPACE}}{'':-<{MAX_WN + MAX_WT + MAX_WV + EXTRA_FILL}}"
                )
            for i, ver in enumerate(lst.versions):
                name = lst.name.split(":")[0] if first_print else ""
                tags = ",".join(lst.versions[i].tags)
                version = ver.version
                size = ver.size
                if filter_by and filter_by not in tags:
                    continue
                print(f"{' ':<{PRE_SPACE}}| ", end="")
                print(f"{name:<{MAX_WN}}| ", end="")
                print(f"{version:{MAX_WV}}| ", end="")
                if show_size:
                    print(f"{size:>{MAX_WS}} | ", end="")
                print(f"{tags:<{MAX_WT}}")
                first_print = False

            if not filter_by:
                print(
                    f"{' ':<{PRE_SPACE}}{'':-<{MAX_WN + MAX_WT + MAX_WV + EXTRA_FILL}}"
                )
    print()


def print_combined_local_remote(tools: dict, show_size=False):
    print(f"\n{' ':<{PRE_SPACE}}{color.BOLD} ", end="")
    print(f"{'Tool name':<{MAX_WN}}", end="")
    print(f"{f'Local Version':{MAX_WV}}", end="")
    print(f"{'Remote Version':<{MAX_WV}}", end="")
    if show_size:
        print(f" {'R. Size':<{MAX_WS}}", end="")
    print(f"{f'Description':<{MAX_WD}}", end="")
    print(f"{color.END}\n")

    for tool in sorted(tools):
        l_version = tools[tool].get("local_version")[:CHARS_TO_SHOW]
        r_version = tools[tool].get("remote_version")[:CHARS_TO_SHOW]
        description = tools[tool].get("description")

        print(f"{' ':<{PRE_SPACE}}|", end="")
        print(f"{tool:<{MAX_WN}}", end="")
        print(f"{l_version:{MAX_WV}}", end="")
        print(f"{r_version:{MAX_WV}}", end="")
        if show_size:
            size = tools[tool].get("compressed_size")
            print(f"{size:>{MAX_WS}} ", end="")
        print(f"{description:<{MAX_WD}}")


def create_head_argparse() -> argparse.ArgumentParser:
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
    m_parser.add_argument(
        "-t",
        "--tools",
        help="Path for 'tools' repository locally. Optionally used for meta files, README updating etc.",
    )
    subparsers = m_parser.add_subparsers(dest="sub_command")
    create_list_argparse(subparsers)
    create_utils_argparse(subparsers)
    return m_parser


def create_utils_argparse(subparsers: argparse._SubParsersAction):
    utility_parser = subparsers.add_parser(
        "utils", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    utility_parser.add_argument(
        "--config", help="Override filepath for registry configuration file.",
    )
    sub_utils_parser = utility_parser.add_subparsers(dest="utils_sub_command")
    readme_parser = sub_utils_parser.add_parser(
        "update-readme",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Update README of tool(s) in Docker Hub. Uses local 'tools' repository as source.",
    )
    readme_exclusive_group = readme_parser.add_mutually_exclusive_group()
    readme_exclusive_group.add_argument(
        "--all",
        help="Update all README files of 'tools' repository into DockerHub.",
        action="store_true",
    )
    readme_exclusive_group.add_argument(
        "-n", "--name", help="Name of the tool to update README in Docker Hub.",
    )


def create_list_argparse(subparsers: argparse._SubParsersAction, ):
    list_parser = subparsers.add_parser(
        "list", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    list_parser.add_argument(
        "--config", help="Override filepath for registry configuration file.",
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
        "-s",
        "--size",
        action="store_true",
        help="Include size in listing. Compressed on remote, uncompressed on local.",
    )
    list_parser.add_argument(
        "-j", "--json", action="store_true", help="Print output in JSON format."
    )
    list_second_exclusive = list_parser.add_mutually_exclusive_group()
    list_second_exclusive.add_argument(
        "-r",
        "--remote",
        action="store_true",
        help="List remote 'cincan' tools from registry.",
    )
    list_second_exclusive.add_argument(
        "-l",
        "--local",
        action="store_true",
        help="List only locally available 'cincan' tools.",
    )
    subsubparsers = list_parser.add_subparsers(dest="list_sub_command")
    version_parser = subsubparsers.add_parser(
        "versions",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="List all versions of the tools.",
    )
    version_exclusive_group = version_parser.add_mutually_exclusive_group()
    version_exclusive_group.add_argument(
        "-n", "--name", help="Check single tool by the name.",
    )
    version_exclusive_group.add_argument(
        "-u",
        "--only-updates",
        action="store_true",
        help="Lists only available updates.",
    )
    version_parser.add_argument(
        "-w", "--with-tags", action="store_true", help="Show tags of latest version.",
    )
    version_parser.add_argument(
        "-f",
        "--force-refresh",
        action="store_true",
        help="Refresh all version related cache data including meta files.",
    )


def list_handler(args):
    if (args.list_sub_command or args.sub_command == "versions") and (
            args.all or args.tag != DEFAULT_IMAGE_FILTER_TAG or args.size
    ):
        logging.getLogger(__name__).warning(
            "No effect with size or tag related arguments when used with 'versions' subcommand"
        )

    # If exported as module and parent parser of 'list' not defining
    if not hasattr(args, "tools"):
        args.tools = ""

    reg = ToolRegistry(args.config, args.tools)

    if not args.list_sub_command:

        if args.local or args.remote:

            loop = asyncio.get_event_loop()
            try:
                tools = loop.run_until_complete(
                    reg.list_tools_local_images(
                        defined_tag=args.tag if not args.all else ""
                    )
                ) if args.local else loop.run_until_complete(
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
                    print(json.dumps(tools, cls=ToolInfoEncoder))
                    exit(0)
                else:
                    print(f"\n  Listing all tools :\n")

                location = "local" if args.local else "remote"

                print_tools_by_location(
                    tools, location, args.tag if not args.all else "", args.size
                )

        else:
            tool_list = reg.list_tools(defined_tag=args.tag if not args.all else "")
            if not args.all and not args.json and tool_list:
                print(f"\n  Listing all tools with tag '{args.tag}':\n")
            if not args.json and tool_list:
                print_combined_local_remote(tool_list, args.size)
            elif tool_list:
                print(json.dumps(tool_list))
            else:
                print("No single tool available for unknown reason.")

    elif args.list_sub_command == "versions":
        loop = asyncio.get_event_loop()
        ret = loop.run_until_complete(
            reg.list_versions(
                tool=args.name or "",
                to_json=args.json or False,
                only_updates=args.only_updates,
                force_refresh=args.force_refresh,
            )
        )
        if args.name and not args.json:
            print_single_tool_version_check(ret, args.with_tags)
        elif not args.name and not args.json:
            loc = "remote" if args.remote else "local"
            print_version_check(ret, loc, args.only_updates, args.with_tags)
        if args.json:
            print(ret)
        loop.close()


def utils_handler(args):
    if args.utils_sub_command == "update-readme":
        reg = HubReadmeHandler(tools_repo_path=args.tools, config_path=args.config)
        if args.all:
            reg.update_readme_all_tools()
        elif args.name:
            reg.update_readme_single_tool(args.name)
        else:
            raise NotImplementedError
    else:
        print("Available subcommands: update-readme")
        sys.exit(1)


def main():
    m_parser = create_head_argparse()

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
        format=f"{' ':<{PRE_SPACE}}%(levelname)s - %(name)s: %(message)s",
        level=getattr(logging, log_level),
    )

    if sub_command == "help":
        m_parser.print_help()
        sys.exit(1)

    elif sub_command == "list":
        list_handler(args)

    elif sub_command == "utils":
        utils_handler(args)
