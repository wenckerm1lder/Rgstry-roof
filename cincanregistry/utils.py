import datetime
import pathlib
import yaml
from typing import List


def parse_file_time(string: str) -> datetime.datetime:
    """Parse time from file as stored by Docker"""
    s = string[0:19]
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")


def format_time(time: datetime.datetime) -> str:
    """Format time as we would like to see it in ISO8601"""
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def split_tool_tag(tag: str) -> (str, str):
    """Split tool tag into tool name and tool version"""
    tag_split = tag.split(":", maxsplit=2)
    return tag_split[0], tag_split[1] if len(tag_split) > 1 else "latest"


def read_index_file(index_f: pathlib.Path) -> List:
    """Get index file, which tells paths for tools
    Should be in the root of cloned https://gitlab.com/CinCan/tools
    """
    if isinstance(index_f, pathlib.Path):
        with index_f.open("r") as f:
            index_f = f.read()
    else:
        raise TypeError("Invalid path format")
    yaml_obj = yaml.safe_load(index_f)
    return yaml_obj.get("tools")
