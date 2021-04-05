import datetime
import logging
import sqlite3
from contextlib import contextmanager
from typing import List, Union, Any, Tuple

from . import ToolInfo
from . import VersionInfo
from .checkers import classmap
from .configuration import Configuration
from .utils import format_time, parse_file_time

# sqlite3.register_adapter(datetime.datetime, adapt_datetime)
TABLE_TOOLS = "tools"
TABLE_METADATA = "metadata"
TABLE_VERSION_DATA = "version_data"

c_tool = f'''CREATE TABLE if not exists {TABLE_TOOLS}(
    name TEXT PRIMARY KEY, -- must be unique, we don't have tools with same names
    updated TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT
);
'''
# For meta_id, refer for available options file cincanregistry.checkers._init_ and classmap
c_metadata = f'''CREATE TABLE if not exists {TABLE_METADATA}(
    meta_id INTEGER PRIMARY KEY,
    tool_id TEXT NOT NULL,
    uri TEXT UNIQUE, -- It should be impossible to be two identical uris for different providers
    repository TEXT NOT NULL,
    tool TEXT NOT NULL,
    provider TEXT NOT NULL, 
    suite TEXT,
    method TEXT NOT NULL, 
    origin INTEGER NOT NULL, 
    docker_origin INTEGER NOT NULL,
    FOREIGN KEY (tool_id)
        REFERENCES {TABLE_TOOLS} (name),
    UNIQUE (uri, repository, tool, provider) ON CONFLICT REPLACE 
);'''

c_version_data = f'''CREATE TABLE if not exists {TABLE_VERSION_DATA}(
    id INTEGER PRIMARY KEY,
    tool_id TEXT NOT NULL,
    meta_id INTEGER,
    version TEXT,
    version_type TEXT,
    source TEXT NOT NULL,
    tags TEXT NOT NULL, -- comma separated string
    updated TEXT NOT NULL,
    origin INTEGER NOT NULL,
    size TEXT NOT NULL,
    created TEXT NOT NULL,
    FOREIGN KEY (meta_id)
        REFERENCES {TABLE_METADATA} (meta_id)
    FOREIGN KEY (tool_id)
        REFERENCES {TABLE_TOOLS} (name),
    -- We should not have duplicate versions from same origin - no use
    UNIQUE (version, version_type, source) ON CONFLICT REPLACE
);'''


# FOREIGN KEY (tool_id)
#     REFERENCES tools (tool_id)


class ToolDatabase:
    def __init__(self, config: Configuration):
        self.logger = logging.getLogger("database")
        try:
            self.db_conn = sqlite3.connect(f"file:{config.tool_db}?mode=rw", uri=True)
            self.db_conn.row_factory = sqlite3.Row
            self.cursor = self.db_conn.cursor()
            self.logger.debug("Database exists already.")
        except sqlite3.OperationalError:
            self.logger.debug("Creating new database file...")
            self.db_conn = sqlite3.connect(str(config.tool_db))
            self.db_conn.row_factory = sqlite3.Row
            self.cursor = self.db_conn.cursor()
            self.configure()
            self.create_tables_if_not_exist()
        self.create_custom_functions()

        # self.create_tables_if_not_exist()

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
        self.db_conn.create_function("s_date", 1, format_time)

    def insert_version_info(self, tool_name: str, version_info: Union[VersionInfo, List[VersionInfo]]):
        """Insert list or single version info of specific tool, referenced by name"""
        if not version_info:
            self.logger.debug("Empty version list provided...nothing to add.")
            return
        v_time = format_time(datetime.datetime.now())
        s_command = f"INSERT INTO {TABLE_VERSION_DATA}(tool_id, meta_id, version, version_type, source, " \
                    f"tags, updated, origin, size, created) VALUES (?,?,?,?,?,?,?,?,?,?)"
        if isinstance(version_info, VersionInfo):
            # Insert raw size, meta_id by checking existing upstream checkers, created time last param
            meta_id = str(version_info.source) if str(version_info.source) in classmap else None
            self.execute(s_command,
                         (tool_name, meta_id, version_info.version, version_info.version_type.value,
                          str(version_info.source),
                          ",".join(list(version_info.tags)), v_time, version_info.origin, version_info.raw_size(),
                          v_time))
        elif isinstance(version_info, List):
            self.logger.debug("Running executemany for insert, NOT logged precisely...")
            # Insert raw size, meta_id by checking existing upstream checkers
            version_list = [(tool_name, str(i.source) if str(i.source) in classmap else None, i.version,
                             i.version_type.value, str(i.source),
                             ",".join(list(i.tags)), v_time, i.origin, i.raw_size(), v_time) for
                            i in version_info]
            self.cursor.executemany(s_command, version_list)

    def insert_tool_info(self, tool_info: Union[ToolInfo, List[ToolInfo]]):
        """Insert ToolInfo object or list of objects with upsert into Database"""
        s_command = f"INSERT INTO {TABLE_TOOLS}(name, updated, location, description) " \
                    f"VALUES (?,?,?,?) ON CONFLICT(name) DO UPDATE SET " \
                    f"updated=excluded.updated, " \
                    f"location=excluded.location, " \
                    f"description=excluded.description " \
                    f"WHERE excluded.updated > {TABLE_TOOLS}.updated"
        if isinstance(tool_info, ToolInfo):
            self.execute(s_command, (tool_info.name,
                                     format_time(tool_info.updated), tool_info.location,
                                     tool_info.description))
            # Local, remote or upstream versions
            self.insert_version_info(tool_info.name, tool_info.versions)
        else:
            self.logger.debug("Running executemany for insert, NOT logged precisely...")
            tool_list = [(i.name, format_time(i.updated), i.location, i.description) for i in tool_info]
            self.cursor.executemany(s_command, tool_list)
            # All versions from all tools
            # Local, remote or upstream versions
            for t in tool_info:
                self.insert_version_info(t.name, t.versions)

    def get_tool_by_name(self, tool_name: str) -> Union[ToolInfo, None]:
        """Get tool by name"""
        self.execute(
            f"SELECT name, updated, location, description from {TABLE_TOOLS} WHERE {TABLE_TOOLS}.name = '{tool_name}'")
        t = self.cursor.fetchone()
        return self.row_into_tool_info_obj(t) if t else None

    def get_tools(self) -> List[ToolInfo]:
        self.execute(f"SELECT name, updated, location, description from {TABLE_TOOLS}")
        rows = self.cursor.fetchall()
        return [self.row_into_tool_info_obj(i) for i in rows]

    def get_versions_by_tool(self, tool_name: str):
        """Get all versions by tool name"""
        s_get_versions = f"SELECT * FROM {TABLE_VERSION_DATA} WHERE tool_id = '{tool_name}';"
        self.execute(s_get_versions)
        rows = self.cursor.fetchall()
        return [self.row_into_version_info_obj(r) for r in rows]

    def get_versions_by_tool_and_source(self, tool_name: str, source: str) -> List[VersionInfo]:
        """Get versions of tool by name and source of the versions"""
        pass

    def row_into_version_info_obj(self, row: sqlite3.Row) -> VersionInfo:
        """Convert Row object into VersionInfo object"""
        try:
            if __debug__:
                self.logger.debug(f"Version size is type of {type(row)}")
            # DB has raw size by default, could be integers instead of strings
            size = int(row["size"])
        except ValueError:
            size = row["size"]
        # No booleans in SQLite, convert integer back
        origin = bool(row["origin"])
        return VersionInfo(version=row["version"], version_type=row["version_type"],
                           source=row["source"],
                           tags=set(row["tags"].split(',')), updated=parse_file_time(row["updated"]),
                           origin=origin, size=size)

    def row_into_tool_info_obj(self, row: sqlite3.Row) -> ToolInfo:
        """Convert Row object into ToolInfo object"""
        if len(row) < 4:
            raise ValueError(f"Row in {TABLE_TOOLS} table should have 4 values.")
        name, updated, location, description = row
        return ToolInfo(name=name, updated=parse_file_time(updated), location=location, description=description,
                        versions=self.get_versions_by_tool(name))

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
