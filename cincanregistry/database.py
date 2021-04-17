import datetime
import logging
import sqlite3
from contextlib import contextmanager
from typing import List, Union, Any, Tuple, Dict

from . import ToolInfo
from . import VersionInfo, VersionType
from .checkers import classmap, UpstreamChecker
from .configuration import Configuration
from .utils import format_time, parse_file_time

# sqlite3.register_adapter(datetime.datetime, adapt_datetime)
TABLE_TOOLS = "tools"
TABLE_METADATA = "metadata"
TABLE_VERSION_DATA = "version_data"
TABLE_META_CONF = "metaconf"
# TABLE_CHECKER = "checker_extra"

c_tool = f'''CREATE TABLE if not exists {TABLE_TOOLS}(
    -- id INTEGER PRIMARY KEY, -- autoincrement could prevent reuse of deleted rows
    name TEXT NOT NULL, -- must be unique with location, we don't have tools with same names
    updated TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '',
    UNIQUE (name, location)
);
'''
# For meta_id, refer for available options file cincanregistry.checkers._init_ and classmap
c_metadata = f'''CREATE TABLE if not exists {TABLE_METADATA}(
    meta_id INTEGER PRIMARY KEY,
    tool_id TEXT NOT NULL,
    tool_location TEXT NOT NULL,
    uri TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '', -- sometimes multiple tools are found from e.g. same GitHub repository
    repository TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '', -- can be empty when debian used for example
    tool TEXT NOT NULL,
    provider TEXT NOT NULL, 
    suite TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '',
    method TEXT NOT NULL, 
    origin INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0, 
    docker_origin INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
    updated TEXT NOT NULL, -- not in provided meta file which is parsed from external source
    FOREIGN KEY (tool_id, tool_location)
        REFERENCES {TABLE_TOOLS} (name, location),
    UNIQUE (uri, repository, tool, provider) ON CONFLICT REPLACE 
);'''

c_version_data = f'''CREATE TABLE if not exists {TABLE_VERSION_DATA}(
    id INTEGER PRIMARY KEY,
    tool_id TEXT NOT NULL,
    tool_location TEXT NOT NULL,
    meta_id INTEGER,
    version TEXT,
    version_type TEXT,
    source TEXT NOT NULL, -- upstream provider, local or remote
    tags TEXT NOT NULL, -- comma separated string
    updated TEXT NOT NULL,
    origin INTEGER NOT NULL,
    size TEXT,
    -- when created in database
    created TEXT NOT NULL,
    extra_info TEXT,
    FOREIGN KEY (meta_id)
        REFERENCES {TABLE_METADATA} (meta_id) ON DELETE CASCADE ,
    FOREIGN KEY (tool_id, tool_location) 
        REFERENCES {TABLE_TOOLS} (name, location) ON DELETE CASCADE ,
    -- We should not have duplicate versions from same origin - no use
    UNIQUE (tool_id, version, version_type, source) ON CONFLICT REPLACE
);'''


# c_checker_extra = f'''CREATE TABLE if not exists {TABLE_CHECKER}(
#     id INTEGER PRIMARY KEY,
#     version_id INTEGER NOT NULL,
#     extra_info TEXT NOT NULL,
#     FOREIGN KEY (version_id)
#         REFERENCES {TABLE_VERSION_DATA} (id) ON DELETE CASCADE ,
# );'''


# FOREIGN KEY (tool_id)
#     REFERENCES tools (tool_id)


class ToolDatabase:
    def __init__(self, config: Configuration):
        self.logger = logging.getLogger("database")
        try:
            self.db_conn = sqlite3.connect(f"file:{config.tool_db}?mode=rw", uri=True, check_same_thread=True)
            self.db_conn.row_factory = sqlite3.Row
            self.cursor = self.db_conn.cursor()
        except sqlite3.OperationalError:
            self.logger.debug("Creating new database file...")
            self.db_conn = sqlite3.connect(str(config.tool_db), check_same_thread=True)
            self.db_conn.row_factory = sqlite3.Row
            self.cursor = self.db_conn.cursor()
            self.configure()
            self.create_tables_if_not_exist()
        self.create_custom_functions()
        self.create_tables_if_not_exist()

    def __del__(self):
        if self.cursor:
            self.cursor.close()
        if self.db_conn:
            self.db_conn.close()

    def execute(self, command: str, params: Any = None):
        """Wrapper for cursor execute"""
        if logging.root.level == logging.DEBUG:
            # On debug mode, gather full commands
            debug_str = command
            if isinstance(params, Tuple):
                for t_val in params:
                    debug_str = debug_str.replace("?", str(t_val), 1)
            elif params:
                debug_str = debug_str.replace("?", params)
            self.logger.debug(debug_str)
        if not params:
            self.cursor.execute(command)
        else:
            self.cursor.execute(command, params)

    def configure(self):
        # Enable Foreign Keys
        self.execute("PRAGMA foreign_keys = ON")
        # Enable multi-read mode
        self.execute("PRAGMA journal_mode = wal")

    def create_tables_if_not_exist(self):
        """Generate all database tables"""
        self.cursor.execute(c_tool)
        self.cursor.execute(c_metadata)
        self.cursor.execute(c_version_data)

    def create_custom_functions(self):
        """Create functions e.g. date time conversion"""
        # self.db_conn.create_function("s_date", 1, format_time)
        pass

    def insert_meta_info(self, tool_name: str, tool_location: str, meta_data: dict):
        v_time = format_time(datetime.datetime.now())
        s_insert_meta = f"INSERT INTO {TABLE_METADATA}(tool_id, tool_location, uri, repository, tool, provider, " \
                        f"suite, method, origin, docker_origin , updated) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        params = [tool_name, tool_location, meta_data.get("uri"), meta_data.get("repository"), meta_data.get("tool"),
                  meta_data.get("provider"), meta_data.get("suite"), meta_data.get("method"), meta_data.get("origin"),
                  meta_data.get("docker_origin"), v_time]
        # Lastrowid could be used on following VersionInfo insert to set
        self.execute(s_insert_meta, tuple(params))

    def insert_version_info(self, tool: ToolInfo, version_info: Union[VersionInfo, List[VersionInfo]]):
        """Insert list or single version info of specific tool, referenced by name"""
        if not version_info:
            self.logger.debug("Empty version list provided...nothing to add.")
            return
        v_time = format_time(datetime.datetime.now())
        s_command = f"INSERT INTO {TABLE_VERSION_DATA}(tool_id, tool_location, meta_id, version, version_type, source, " \
                    f"tags, updated, origin, size, created) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        if isinstance(version_info, VersionInfo):
            # Insert raw size, meta_id by checking existing upstream checkers, created time last param
            if isinstance(version_info.source, UpstreamChecker):
                meta_id = self.get_meta_id(tool.name, version_info.source)
            else:
                meta_id = None
            u_time = format_time(version_info.updated) if version_info.updated else v_time
            self.execute(s_command,
                         (tool.name, tool.location, meta_id, version_info.version, version_info.version_type.value,
                          str(version_info.source),
                          ",".join(list(version_info.tags)), u_time, version_info.origin, version_info.raw_size(),
                          v_time))
        elif isinstance(version_info, List):
            self.logger.debug("Running executemany for insert, NOT logged precisely...")
            # Insert raw size, meta_id by checking existing upstream checkers
            version_list = [(tool.name, tool.location, str(i.source) if str(i.source) in classmap else None, i.version,
                             i.version_type.value, str(i.source),
                             ",".join(list(i.tags)), format_time(i.updated) if i.updated else v_time, i.origin,
                             i.raw_size(), v_time)
                            for
                            i in version_info]
            self.cursor.executemany(s_command, version_list)

    def insert_tool_info(self, tool_info: Union[ToolInfo, List[ToolInfo]]):
        """Insert ToolInfo object or list of objects with upsert into Database"""
        s_command = f"INSERT INTO {TABLE_TOOLS}(name, updated, location, description) " \
                    f"VALUES (?,?,?,?) ON CONFLICT(name, location) DO UPDATE SET " \
                    f"updated=excluded.updated, " \
                    f"location=excluded.location, " \
                    f"description=excluded.description " \
                    f"WHERE excluded.updated > {TABLE_TOOLS}.updated"
        if isinstance(tool_info, ToolInfo):
            self.execute(s_command, (tool_info.name,
                                     format_time(tool_info.updated), tool_info.location,
                                     tool_info.description))
            # Local, remote or upstream versions
            self.insert_version_info(tool_info, tool_info.versions)
        else:
            self.logger.debug("Running executemany for insert, NOT logged precisely...")
            tool_list = [(i.name, format_time(i.updated), i.location, i.description) for i in tool_info]
            self.cursor.executemany(s_command, tool_list)
            # All versions from all tools
            # Local, remote or upstream versions
            for t in tool_info:
                self.insert_version_info(t, t.versions)

    def get_meta_id(self, tool_name: str, checker: UpstreamChecker) -> int:
        """Get meta id for matching Checker configuration, based on Unique constraint"""
        params = [tool_name, checker.uri, checker.repository, checker.tool, checker.provider]
        s_get_meta = f"SELECT meta_id FROM {TABLE_METADATA} WHERE tool_id = ? AND uri = ?" \
                     " AND repository = ? AND tool = ? AND provider = ? "
        self.execute(s_get_meta, tuple(params))
        meta_id = self.cursor.fetchone()
        if meta_id:
            return meta_id["meta_id"]
        else:
            # Less accurate match
            s_get_meta = f"SELECT meta_id FROM {TABLE_METADATA} WHERE tool_id = ? AND tool = ? AND provider = ? "
            params = [tool_name, checker.tool, checker.provider]
            self.execute(s_get_meta, tuple(params))
            meta_id = self.cursor.fetchone()
            if meta_id:
                return meta_id["meta_id"]
            else:
                return None

    def get_single_tool(self, tool_name: str, remote_name: str = "", filter_by: [VersionType] = None) -> Union[
        ToolInfo, None]:
        """Get tool by name, filter by included versions"""
        params = [tool_name]
        command = f"SELECT name, updated, location, description from {TABLE_TOOLS} " \
                  f"WHERE {TABLE_TOOLS}.name = ?"
        if remote_name:
            command += f" AND {TABLE_TOOLS}.location = ?"
            params.append(remote_name)
        self.execute(command, tuple(params))
        t = self.cursor.fetchone()
        return self.row_into_tool_info_obj(t, filter_by) if t else None

    def get_tools(self, remote_name: str = "", filter_by: [VersionType] = None, by_time: datetime.datetime = None) -> List[ToolInfo]:
        """Get tools, filter by remote name or updated time
        TODO implement time filter
        Only remote tool information is stored into database
        """
        command = f"SELECT name, updated, location, description from {TABLE_TOOLS}"
        params = []
        if remote_name:
            command += f" WHERE {TABLE_TOOLS}.location = ?"
            params.append(remote_name)
        self.execute(command, tuple(params))
        rows = self.cursor.fetchall()
        return [self.row_into_tool_info_obj(i, filter_by=filter_by) for i in rows]

    def get_versions_by_tool(self, tool_name: str, version_type: [VersionType] = None, provider: str = "",
                             latest: bool = False) -> Union[List[VersionInfo], VersionInfo]:
        """Get all versions by tool name, by version_type, provider if set
        return single VersionInfo object if latest set
        """
        s_get_versions = f"SELECT * FROM {TABLE_VERSION_DATA} WHERE tool_id = ?"
        params = [tool_name]
        if version_type:
            if not isinstance(version_type, List):
                self.logger.error(
                    "Wrong format for parameter 'version_type' when getting versions by tool. Should be list.")
                return []
            self.logger.debug(f"getting versions by type(s) : {[v for v in version_type]}")
            # Dynamically generate sql for all version types
            for i, v_t in enumerate(version_type):
                if i == 0:
                    s_get_versions += f" AND (version_type = ?"
                else:
                    s_get_versions += f" OR version_type = ?"
                params.append(v_t.value)
            s_get_versions += ")"
        if provider:
            s_get_versions += f" AND source = ?"
            params.append(provider)
        if latest:
            s_get_versions += f" ORDER BY updated DESC LIMIT 1"

        self.execute(s_get_versions, tuple(params))
        if latest:
            row = self.cursor.fetchone()
            if not row:
                return None
            return self.row_into_version_info_obj(row)
        rows = self.cursor.fetchall()
        if not rows:
            self.logger.debug(f"No versions found for tool {tool_name} by type {version_type} and provider {provider}")
            return []
        return [self.row_into_version_info_obj(r) for r in rows]

    def get_meta_information(self, tool_name: str, provider: str = "", meta_id: str = "") -> List[Dict]:
        params = [tool_name]
        s_get_meta = f"SELECT * FROM {TABLE_METADATA} WHERE tool_id = ?"
        if meta_id and provider:
            self.logger.debug("Both provider and meta_id supplied for meta information query, ignoring provider...")
            self.logger.debug(f"Provider: {provider} Meta id: {meta_id}")
        if provider and not meta_id:
            s_get_meta += " AND provider = ?"
            params.append(provider)
        if meta_id:
            s_get_meta += " AND meta_id = ?"
            params.append(meta_id)
        # Ignore case
        s_get_meta += " COLLATE NOCASE;"
        self.execute(s_get_meta, tuple(params))
        rows = self.cursor.fetchall()
        if len(rows) > 1 and provider:
            self.logger.error(
                f"Possible duplicates for meta data for tool {tool_name} with provider {provider}. Report bug.")
        if len(rows) >= 1:
            return [dict(i) for i in rows]
        else:
            return []

    def row_into_version_info_obj(self, row: sqlite3.Row) -> VersionInfo:
        """Convert Row object into VersionInfo object"""
        try:
            # DB has raw size by default, could be integers instead of strings
            size = int(row["size"])
        except (ValueError, TypeError):
            size = row["size"]
        # No booleans in SQLite, convert integer back
        origin = bool(row["origin"])
        if row["source"] and (row["source"].lower() in classmap.keys()):
            # If meta_id exist, query prioritizes it.
            upstream_info = self.get_meta_information(row["tool_id"], row["source"], row["meta_id"])
            if upstream_info:
                dummy_checker = classmap.get(row["source"].lower())(
                    upstream_info[0],
                    version=row["version"],
                    extra_info=row["extra_info"],
                )
            else:
                self.logger.debug(f"No meta information for tool {row['tool_id']} found.")
                dummy_checker = None
        else:
            dummy_checker = None
        return VersionInfo(version=row["version"], version_type=row["version_type"],
                           source=dummy_checker or row["source"],
                           tags=set(row["tags"].split(',')), updated=parse_file_time(row["updated"]),
                           origin=origin, size=size)

    def row_into_tool_info_obj(self, row: sqlite3.Row, filter_by: [VersionType] = None) -> ToolInfo:
        """Convert Row object into ToolInfo object. Get related versions which can be filtered by VersionType"""
        if len(row) < 4:
            raise ValueError(f"Row in {TABLE_TOOLS} table should have 4 values.")
        name, updated, location, description = row
        return ToolInfo(name=name, updated=parse_file_time(updated), location=location, description=description,
                        versions=self.get_versions_by_tool(name, version_type=filter_by))

    @contextmanager
    def transaction(self):
        # We must issue a "BEGIN" explicitly when running in auto-commit mode.
        self.db_conn.execute('BEGIN')
        try:
            # Yield control back to the caller.
            yield
        except sqlite3.Error:
            self.db_conn.rollback()  # Roll back all changes if an exception occurs.
            raise
        else:
            self.db_conn.commit()
