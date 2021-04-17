import re
from datetime import datetime, timedelta
from enum import Enum, unique
from typing import List, Union

from cincanregistry.checkers import UpstreamChecker
from cincanregistry.utils import format_time, parse_file_time


@unique
class VersionType(Enum):
    """There can be following types of different versions"""
    LOCAL = "local"  # On your machine
    REMOTE = "remote"  # On remote Docker registry e.g. Quay
    UPSTREAM = "upstream"  # Origin of the tool, e.g. GitHub
    UNDEFINED = "undefined"


class VersionInfo:
    def __init__(
            self,
            version: str,
            version_type: VersionType,
            source: Union[str, UpstreamChecker],
            tags: set,
            updated: datetime = None,
            origin: bool = False,
            size: Union[int, float] = None,
    ):
        self._version: str = str(version)
        if not isinstance(version_type, VersionType):
            self._version_type = VersionType(value=version_type)
        else:
            self._version_type: VersionType = version_type
        self._source: Union[str, UpstreamChecker] = source
        self._origin: bool = origin
        self._tags: set = tags
        if updated and not isinstance(updated, datetime):
            raise ValueError("Given time is not 'datetime' object.")
        self._updated: datetime = updated
        # Size should be in bytes
        self._size: Union[float, int, str] = size

    @property
    def version(self) -> str:
        """
        Returns version of the object, also check UpstreamChecker
        """
        if isinstance(self._source, UpstreamChecker):
            # Checker might have stored version, prioritize it
            if (not self._version and self._source.version) or (self._version and self._source.version):
                self._version = self._source.version
        return self._version

    @version.setter
    def version(self, version: Union[str, int, float]):
        """Sets 'versions' attribute to new value, does not accept empty value"""
        if not version:
            raise ValueError("Cannot set empty value for version.")
        self._version = str(version)

    @property
    def version_type(self) -> VersionType:
        return self._version_type

    @version_type.setter
    def version_type(self, version_type: VersionType):
        """Set type of Version (see enum VersionType)"""
        if not version_type:
            raise ValueError("Cannot set empty value for type.")
        self._version_type = version_type

    @property
    def provider(self) -> str:
        """Returns provider of upstream source, eg. GitHub """
        if isinstance(self._source, UpstreamChecker):
            return self._source.provider
        else:
            return self._source

    @property
    def docker_origin(self) -> bool:
        """
        Returns true if this upstream is used to install tool in
        corresponding dockerfile.
        """
        if isinstance(self._source, UpstreamChecker):
            return self._source.docker_origin
        else:
            return False

    @property
    def extra_info(self) -> str:
        """Returns possible added extra information."""
        if isinstance(self._source, UpstreamChecker):
            return self._source.extra_info
        else:
            return ""

    @property
    def source(self) -> UpstreamChecker:
        return self._source

    @source.setter
    def source(self, checker: Union[str, UpstreamChecker]):
        self._source = checker

    @property
    def origin(self) -> bool:
        if isinstance(self._source, UpstreamChecker):
            self._origin = self._source.origin
        return self._origin

    @property
    def tags(self) -> set:
        return self._tags

    @property
    def updated(self) -> datetime:
        return self._updated

    @updated.setter
    def updated(self, dt: datetime):
        """Sets 'updated' attribute to new value, only 'datetime' object is valid"""
        if not isinstance(dt, datetime):
            raise ValueError("Given time is not 'datetime' object.")
        self._updated = dt

    @property
    def size(self) -> str:
        """
        Return size in bigger units
        """
        if isinstance(self._size, str):
            # It is possible that class is instanced from old values
            if (
                    self._size.endswith(" bytes")
                    or self._size.endswith(" KB")
                    or self._size.endswith(" MB")
                    or self._size.endswith(" GB")
            ):
                return self._size
            else:
                return "NaN"
        if self._size is None:
            return "NaN"
        if self._size < 1000:
            return f"{self._size} bytes"
        size = self._size / 1000
        if size < 1000:
            return f"{size:0.2f} KB"
        size /= 1000
        if size < 1000:
            return f"{size:0.2f} MB"
        size /= 1000
        if size < 1000:
            return f"{size:0.2f} GB"

    def raw_size(self) -> Union[int, str]:
        return self._size

    @size.setter
    def size(self, value: Union[int, float]):
        """Size as integer or float, expected to be in bytes"""
        if isinstance(value, float) or isinstance(value, int):
            self._size = value
        else:
            raise ValueError("Given size for image is not float or integer.")

    def _normalize(self, value: str) -> Union[str, List]:
        """
        Method for normalizing version strings. It attempts to make map based 
        on potential version number part of the string, which is comparable.
        Potential hashes are returned as they are, as well strings without any digits.
        """
        if any(char.isdigit() for char in value):
            # Git uses SHA-1 hash currently, length 40 characters
            # Commit hash maybe
            if re.findall(r"(^[a-fA-F0-9]{40}$)", value):
                return value
            # In future, SHA-256 will be used for commit hash, length is 64 chars
            elif re.findall(r"(^[a-fA-F0-9]{64}$)", value):
                return value
            else:
                # Subtract else than numbers and '.' and '_'
                sub = re.sub(r"[^0-9._]+", "", value)
                # Replace dash with dot, seems to be commonly used with similar purpose
                rep = sub.replace("_", ".")
                split_by_dot = re.split(r"[._]", rep)
                first = None
                second = None
                # Get slice from list, which is expected to contain version information
                # NOTE not 100% working, but maybe 99%
                for i, val in enumerate(split_by_dot):
                    if not val and not first:
                        first = i + 1
                        continue
                    if val == "" and first:
                        second = i
                        break
                return list(map(int, split_by_dot[first:second]))
        else:
            return value

    def get_normalized_ver(self) -> List:
        """Normalize version number of this instance"""
        return self._normalize(self.version)

    def __eq__(self, value: Union[str, "VersionInfo"]) -> bool:
        """
        Support comparison between strings or other VersionInfo objects
        """
        if isinstance(value, str):
            if self.get_normalized_ver() == self._normalize(value):
                return True
            else:
                return False
        elif not isinstance(value, VersionInfo):
            raise ValueError(
                f"Unable to compare '=' type {type(value)} and type {type(VersionInfo)}"
            )
        else:
            if self.get_normalized_ver() == value.get_normalized_ver():
                return True
            else:
                return False

    def __str__(self) -> str:
        return str(self.version)

    def __format__(self, value):
        return self.version.__format__(value)

    def __iter__(self):
        yield "version", self.version,
        yield "version_type", self.version_type.value
        yield "source", self.source if isinstance(self.source, str) else dict(
            self.source
        ),
        yield "tags", sorted(list(self.tags)),
        yield "updated", format_time(self.updated),
        yield "origin", self.origin,
        yield "size", self.size

    @classmethod
    def from_dict(cls, _dict: dict):
        """Create VersionInfo object from dictionary"""
        if not isinstance(_dict, dict):
            raise TypeError(
                "No dictionary provided when instancing VersionInfo with 'from_dict'"
            )
        params = {}
        for k, v in _dict.items():
            if k == "tags":
                params[k] = set(v)
            elif k == "updated":
                params[k] = parse_file_time(v)
            else:
                params[k] = v
        return cls(**params)
