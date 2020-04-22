from datetime import datetime, timedelta
from typing import List, Union
from collections.abc import Iterable
from .checkers._checker import UpstreamChecker
import re
import json


class VersionInfo:
    def __init__(
        self,
        version: str,
        source: Union[str, UpstreamChecker],
        tags: set,
        updated: datetime = None,
        origin: bool = False,
    ):
        self._version: str = str(version)
        self._source: Union[str, UpstreamChecker] = source
        self._origin: bool = origin
        self._tags: set = tags
        self._updated: datetime = updated

    @property
    def version(self) -> str:
        """
        Returns version of the object. If it's containing information
        about possible upstream version, updates it if it's older than 1 hour.
        """
        if isinstance(self._source, UpstreamChecker):
            now = datetime.now()
            if not self._updated or not (
                now - timedelta(hours=1) <= self._updated <= now
            ):
                self._version = self._source.get_version()
                self._updated = now
                return self._version
            else:
                self._version = self._source.version
        return self._version

    @version.setter
    def version(self, version: Union[str, int, float]):
        if not version:
            raise ValueError("Cannot set empty value for version.")
        self._version = str(version)

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
        Returns true if this upsream is used to install tool in
        corresponding dockerfile.
        """
        if isinstance(self._source, UpstreamChecker):
            return self._source.docker_origin
        else:
            return False

    @property
    def extraInfo(self) -> str:
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
    def origin(self) -> str:
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
        if not isinstance(dt, datetime):
            raise ValueError("Given time is not 'datetime' object.")
        self._updated = dt

    def get_normalized_ver(self) -> List:
        if any(char.isdigit() for char in self.version):
            # Git uses SHA-1 hash currently, length 40 characters
            # Commit hash maybe
            if re.findall(r"(^[a-fA-F0-9]{40}$)", self.version):
                return self.version
            # In future, SHA-256 will be used for commit hash, length is 64 chars
            elif re.findall(r"(^[a-fA-F0-9]{64}$)", self.version):
                return self.version
            else:
                return list(map(int, re.sub(r"[^0-9.]+", "", self.version).split(".")))
        else:
            return self.version

    def __eq__(self, value) -> bool:
        if not isinstance(value, VersionInfo):
            raise ValueError(
                f"Unable to compare '=' type {type(value)} and type {type(VersionInfo)}"
            )
        else:
            if self.get_normalized_ver() == value.get_normalized_ver():
                return True
            else:
                return False

    def __str__(self):
        return str(self.version)

    def __format__(self, value):
        return self.version.__format__(value)

    def __iter__(self):
        yield "version", self.version,
        yield "source", self.source if isinstance(self.source, str) else dict(
            self.source
        ),
        yield "tags", sorted(list(self.tags)),
        yield "updated", str(self.updated),
        yield "origin", self.origin,

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
        as very origin of the tool.
        """
        if self.upstream_v:
            for v in self.upstream_v:
                if v.origin:
                    return v
        return VersionInfo("Not implemented", "", set(), datetime.min)

    def getDockerOriginVersion(self) -> VersionInfo:
        """
        Returns version from the upstream versions, which is marked
        as install source in dockerfile.
        """
        if self.upstream_v:
            for v in self.upstream_v:
                if v.docker_origin:
                    return v
        return VersionInfo("Not implemented", "", set(), datetime.min)

    def getLatest(self, in_upstream: bool = False) -> VersionInfo:
        """
        Attempts to return latest version from available versions.
        getOriginVersion method is expected to return latest, if origin
        is found.
        """
        latest = next(
            iter(
                sorted(
                    self.versions
                    if not in_upstream
                    else (self.upstream_v if self.upstream_v else []),
                    reverse=True,
                    key=lambda s: self._map_sub_versions(s),
                )
            ),
            None,
        )
        if not latest:
            return VersionInfo("undefined", "", set(), datetime.min)
        else:
            return latest

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
