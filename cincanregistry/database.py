import sqlite3
import logging
import pathlib
from contextlib import contextmanager
from .configuration import Configuration
from . import ToolInfo
from . import VersionInfo
import datetime

# sqlite3.register_adapter(datetime.datetime, adapt_datetime)

c_tool = '''CREATE TABLE if not exists tools(
    name TEXT PRIMARY KEY, -- must be unique, we don't have tools with same names
    updated TEXT NOT NULL,
    location TEXT NOT NULL,
    versions INTEGER,
    description TEXT
);
'''

c_metadata = '''CREATE TABLE if not exists metadata(
    meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id INTEGER NOT NULL,
    uri TEXT UNIQUE, -- It should be impossible to be two identical uris for different providers
    repository TEXT NOT NULL,
    tool TEXT NOT NULL,
    provider TEXT NOT NULL, 
    suite TEXT,
    method TEXT NOT NULL, 
    origin INTEGER NOT NULL, 
    docker_origin INTEGER NOT NULL,
    FOREIGN KEY (tool_id)
        REFERENCES tools (name)
);'''

c_version_data = '''CREATE TABLE if not exists version_data(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_id INTEGER NOT NULL,
    version TEXT,
    provider TEXT NOT NULL,
    created TEXT NOT NULL

    FOREIGN KEY (meta_id)
        REFERENCES c_metadata (meta_id)
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

        # self.create_tables_if_not_exist()

    def execute(self, command: str):
        """Wrapper for cursor execute"""
        self.cursor.execute(command)

    def configure(self):
        # Enable Foreign Keys
        self.execute("PRAGMA foreign_keys = ON")
        self.execute("PRAGMA journal_mode = wal")

    def create_tables_if_not_exist(self):
        self.cursor.execute(c_tool)
        self.cursor.execute(c_metadata)
        self.cursor.execute(c_version_data)

    def insert_tool_info(self, tool_info: ToolInfo):
        """Insert ToolInfo object with upsert into Database"""
        pass

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