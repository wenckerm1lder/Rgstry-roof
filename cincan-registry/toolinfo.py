from datetime import datetime
from typing import List
from collections import Iterable
import re
import json


class VersionInfo:
    def __init__(
        self,
        version: str,
        source: str,
        tags: set,
        updated: datetime,
        origin: bool = False,
    ):
        self._version: str = version
        self._source: str = source
        self._origin: bool = origin
        self._tags: set = tags
        self._updated: datetime = updated

    @property
    def version(self) -> str:
        return self._version

    @property
    def source(self) -> str:
        return self._source

    @property
    def origin(self) -> str:
        return self._origin

    @property
    def tags(self) -> set:
        return self._tags

    @property
    def updated(self) -> datetime:
        return self._updated

    def get_normalized_ver(self) -> List:
        if any(char.isdigit() for char in self.version):
            # Git uses SHA-1 hash currently, length 40 characters
            # Commit hash maybe
            if re.findall("([a-fA-F0-9\d]{40})", self.version):
                return self.version
            # In future, SHA-256 will be used for commit hash, length is 64 chars
            elif re.findall("([a-fA-F0-9\d]{64})", self.version):
                return self.version
            else:
                return list(map(int, re.sub(r"[^0-9.]+", "", self.version).split(".")))
        else:
            return self.version

    def __eq__(self, value) -> bool:
        if not isinstance(value, VersionInfo):
            raise ValueError(
                f"Unable to compare '=' type {type(value)} and type {self}"
            )
        else:
            if self.get_normalized_ver() == value.get_normalized_ver():
                return True
            else:
                return False

    def __str__(self):
        return self.version

    def __format__(self, value):
        return self.version.__format__(value)

    def toJSON(self):
        """
        Return JSON representation of object
        """
        return json.dumps(
            self,
            default=lambda o: o.__dict__
            if hasattr(o, "__dict__")
            else (list(o) if isinstance(o, Iterable) else str(o)),
            sort_keys=True,
        )
        # return {
        #     "version": self.version,
        #     "source": self.source,
        #     "updated": self.updated,
        #     "tags": list(self.tags),
        # }


# class UpstreamVersion(VersionInfo):
#     def __init__(self, version):
#         super().__init__(version, set({'latest'}), datetime.now())


class ToolInfo:
    """A tool in registry"""

    def __init__(
        self,
        name: str,
        updated: datetime,
        destination: str,
        versions: List[VersionInfo] = [],
        description: str = "",
    ):
        self.name: str = name
        self.updated: str = updated
        self.destination: str = destination
        self.versions: List[VersionInfo] = versions
        self.upstream_v: List[VersionInfo] = []
        self.description = description

    def _map_sub_versions(self, ver: VersionInfo):

        norm_ver = ver.get_normalized_ver()

        # Can't map if there are only  non-digits or hash
        if isinstance(norm_ver, str):
            return [-1]

        else:
            return norm_ver

    def getOriginVersion(self) -> VersionInfo:
        """
        Returns version from the upstream versions, which is marked
        as origin of the tool.
        """
        if self.upstream_v:
            for v in self.upstream_v:
                if v.origin:
                    return v
        return VersionInfo("Not implemented", "", set(), datetime.min)

    def getLatest(self) -> VersionInfo:
        """
        Attempts to return latest version from available versions.
        getOriginVersion method is expected to return latest, if origin
        is found.
        """
        return next(
            iter(
                sorted(
                    self.versions,
                    reverse=True,
                    key=lambda s: self._map_sub_versions(s),
                )
            )
        )

    def __str__(self):
        return "{} {}".format(self.name, self.description)

    def __eq__(self, value) -> bool:
        """
        Compares latest versions between two ToolInfo object.
        """
        if not isinstance(value, ToolInfo):
            raise ValueError(
                f"Unable to compare '=' type {type(value)} and type {self}"
            )
        if self.getLatest() == value.getLatest() and self.name == value.name:
            return True
        else:
            return False
