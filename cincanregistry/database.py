import sqlite3
import logging
import datetime
import pathlib
from contextlib import contextmanager
from typing import List, Union, Any, Tuple
from .configuration import Configuration
from .utils import format_time, parse_file_time
from .checkers import classmap
from . import ToolInfo
from . import VersionInfo
import datetime

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
    meta_id TEXT PRIMARY KEY,
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
        REFERENCES {TABLE_TOOLS} (name)
);'''

c_version_data = f'''CREATE TABLE if not exists {TABLE_VERSION_DATA}(
    id INTEGER PRIMARY KEY,
    tool_id INTEGER NOT NULL,
    meta_id TEXT,
    version TEXT,
    source TEXT NOT NULL,
    origin INTEGER NOT NULL,
    tags TEXT NOT NULL,
    size TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    FOREIGN KEY (meta_id)
        REFERENCES {TABLE_METADATA} (meta_id)
    FOREIGN KEY (tool_id)
        REFERENCES {TABLE_TOOLS} (name)
);'''


# FOREIGN KEY (tool_id)
#     REFERENCES tools (tool_id)


class ToolDatabase:
    def __init__(self, config: Configuration):
        self.logger = logging.getLogger("database")
        try:
            self.db_conn = sqlite3.connect(f"file:{config.tool_db}?mode=rw", uri=True)
            self.cursor = self.db_conn.cursor()
            self.logger.debug("Database exists already.")
        except sqlite3.OperationalError:
            self.logger.debug("Creating new database file...")
            self.db_conn = sqlite3.connect(str(config.tool_db))
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
        s_command = f"INSERT INTO {TABLE_VERSION_DATA}(tool_id, meta_id, version, source, " \
                    f"origin, tags, size, created, updated) VALUES (?,?,?,?,?,?,?,?,?)"
        if isinstance(version_info, VersionInfo):
            meta_id = str(version_info.source) if str(version_info.source) in classmap else ""
            self.execute(s_command,
                         (tool_name, meta_id, version_info.version, version_info.source, version_info.origin,
                          ",".join(list(version_info.tags)), version_info.size, v_time, v_time))
        elif isinstance(version_info, List):
            self.logger.debug("Running executemany for insert, NOT logged precisely...")
            version_list = [(tool_name, str(i.source) if str(i.source) in classmap else "", i.version, i.source,
                             i.origin, ",".join(list(i.tags)), i.size, v_time, v_time) for
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
            # Local or remote versions
            self.insert_version_info(tool_info.name, tool_info.versions)
            # Upstream versions
            self.insert_version_info(tool_info.name, tool_info.upstream_v)
        else:
            self.logger.debug("Running executemany for insert, NOT logged precisely...")
            tool_list = [(i.name, format_time(i.updated), i.location, i.description) for i in tool_info]
            self.cursor.executemany(s_command, tool_list)

    def get_tools(self) -> List[ToolInfo]:
        with self.transaction():
            self.execute(f"SELECT name, updated, location, description from {TABLE_TOOLS}")
            rows = self.cursor.fetchall()
            return [self.row_into_tool_info_obj(i) for i in rows]

    @staticmethod
    def row_into_version_info_obj(row: sqlite3.Row) -> VersionInfo:
        """Convert Row object into VersionInfo object"""
        # if len(row) < 4:
        #     raise ValueError(f"Row in {TABLE_TOOLS} table should have 4 values.")

        pass

    @staticmethod
    def row_into_tool_info_obj(row: sqlite3.Row) -> ToolInfo:
        """Convert Row object into ToolInfo object"""
        if len(row) < 4:
            raise ValueError(f"Row in {TABLE_TOOLS} table should have 4 values.")
        name, updated, location, description = row
        return ToolInfo(name=name, updated=parse_file_time(updated), location=location, description=description)

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
