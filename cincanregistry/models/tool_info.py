from datetime import datetime
from json import JSONEncoder
from typing import List

from cincanregistry.models.version_info import VersionInfo, VersionType
from cincanregistry.utils import format_time, parse_file_time

LATEST_TAG = "latest"


def _map_sub_versions(ver: VersionInfo):
    norm_ver = ver.get_normalized_ver()
    # Can't map if there are only  non-digits or hash
    if isinstance(norm_ver, str):
        return [-1]
    else:
        return norm_ver


class ToolInfo:
    """A tool in registry"""

    def __init__(
            self,
            name: str,
            updated: datetime,
            location: str,
            description: str = "",
            versions: List[VersionInfo] = None,
            meta_hash: str = ""
    ):

        if not name or not isinstance(name, str):
            raise ValueError("Tool must have name in string format.")
        self._name: str = name
        self._updated: datetime = updated
        self.location: str = location  # local daemon, remote name
        self.versions: List[VersionInfo] = versions or []  # Local, Remote, Upstream see class VersionType
        self.description = description
        if meta_hash and not meta_hash.startswith("sha256:") and len(meta_hash) != 71:
            raise ValueError("Hash must start with 'sha256:' and length must be 71")
        self._meta_hash = meta_hash  # Hash value of blob containing meta information for fetching upstream info

    @property
    def name(self) -> str:
        return self._name

    @property
    def updated(self) -> datetime:
        return self._updated

    @updated.setter
    def updated(self, dt: datetime):
        if not isinstance(dt, datetime):
            raise ValueError("Given time is not 'datetime' object.")
        self._updated = dt

    @property
    def meta_hash(self) -> str:
        return self._meta_hash

    @meta_hash.setter
    def meta_hash(self, m_hash: str):
        if not m_hash.startswith("sha256:") and len(m_hash) != 71:
            raise ValueError("Meta hash must start with 'sha256:' and length must be 71")
        self._meta_hash = m_hash

    def _get_origin_version(self, for_docker: bool = False) -> VersionInfo:
        """Method for finding either origin or docker origin version"""
        v_origin = None
        versions = []
        if self.versions:
            for v in self.versions:
                if v.version_type == VersionType.UPSTREAM:
                    if v.origin:
                        versions.append(v)
                    elif for_docker and v.docker_origin:
                        versions.append(v)
        v_origin = self._latest_by_time(versions)
        if v_origin:
            return v_origin
        else:
            return VersionInfo("Not implemented", VersionType.UNDEFINED, "", set(), datetime.min)

    def get_origin_version(self) -> VersionInfo:
        """
         Returns version from the upstream versions, which is marked
         as very origin of the tool.
         """
        return self._get_origin_version()

    def get_docker_origin_version(self) -> VersionInfo:
        """
         Returns version from the upstream versions, which is marked
         as install source for Dockerfile.
         """
        return self._get_origin_version(for_docker=True)

    def _latest_by_time(self, versions: List[VersionInfo]) -> VersionInfo:
        """Return latest version by time from given list"""
        return next(
            iter(
                sorted(
                    versions,
                    reverse=True,
                    key=lambda s: s.updated,
                )
            ),
            None,
        )

    def get_latest(self, in_upstream: bool = False, in_remote: bool = False) -> VersionInfo:
        """
         Attempts to return latest version from available versions. Excluding upstream by default
         By default, not checking upstream
         """
        if in_upstream and not in_remote:
            to_include = [i for i in self.versions if i.version_type == VersionType.UPSTREAM]
            # Iterate only versions which are marked as origin if exist
            origin_v = [i for i in to_include if i.origin]
            if origin_v:
                to_include = origin_v
        elif in_remote and not in_upstream:
            # Return version with 'latest' tag, if multiple, latest by time
            to_include = [i for i in self.versions if i.version_type == VersionType.REMOTE and LATEST_TAG in i.tags]
            if to_include:
                return self._latest_by_time(to_include)
            else:
                return VersionInfo("undefined", VersionType.UNDEFINED, "", set(), datetime.min)

        else:
            to_include = [v for v in self.versions if v.version_type != VersionType.UPSTREAM]

        latest = next(
            iter(
                sorted(
                    to_include,
                    reverse=True,
                    key=lambda s: _map_sub_versions(s),
                )
            ),
            None,
        )
        if not latest:
            return VersionInfo("undefined", VersionType.UNDEFINED, "", set(), datetime.min)
        else:
            return latest

    def __iter__(self):
        yield "name", self.name,
        yield "updated", format_time(self.updated),
        yield "location", self.location,
        yield "versions", [dict(v) for v in self.versions],
        # if self.upstream_v:
        #     yield "upstream_v", [dict(v) for v in self.upstream_v],
        yield "description", self.description
        yield "meta_hash", self.meta_hash

    def __str__(self):
        return f"{self.name} {self.description}"

    def __eq__(self, value) -> bool:
        """
        Compares latest versions between two ToolInfo object.
        """
        if not isinstance(value, ToolInfo):
            raise ValueError(
                f"Unable to compare '=' type {type(value)} and type {self}"
            )
        if self.get_latest() == value.get_latest() and self.name == value.name:
            return True
        else:
            return False

    @classmethod
    def from_dict(cls, _dict: dict):
        """Instance class from dictionary"""
        if not isinstance(_dict, dict):
            raise TypeError(
                "No dictionary provided when instancing ToolInfo with 'from_dict'"
            )
        params = {}
        for k, v in _dict.items():
            if k == "updated":
                params[k] = parse_file_time(v)
            elif k == "versions":
                params[k] = [VersionInfo.from_dict(ver) for ver in v] if v else []
            # elif k == "upstream_v":
            #     params[k] = [VersionInfo.from_dict(ver) for ver in v] if v else []
            else:
                params[k] = v

        return cls(**params)


class ToolInfoEncoder(JSONEncoder):
    """Convert object into JSON"""

    def default(self, o):
        return dict(o)
