import datetime
from typing import List


def parse_file_time(string: str) -> datetime.datetime:
    """Parse time from file as stored by Docker"""
    s = string[0:19]
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")


def format_time(time: datetime.datetime) -> str:
    """Format time as we would like to see it"""
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def parse_data_types(string: str) -> List[str]:
    """Parse list of data types into a list"""
    s = string.strip()
    if len(s) == 0:
        return []
    return list(map(lambda x: x.strip(), s.split(",")))


def split_tool_tag(tag: str) -> (str, str):
    """Split tool tag into tool name and tool version"""
    tag_split = tag.split(":", maxsplit=2)
    return tag_split[0], tag_split[1] if len(tag_split) > 1 else "latest"
