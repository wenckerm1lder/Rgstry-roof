import sqlite3
import pathlib
from contextlib import contextmanager
from configuration import Configuration
import datetime

# sqlite3.register_adapter(datetime.datetime, adapt_datetime)

c_tool = '''CREATE TABLE tools(
    tool_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, 
    updated TEXT NOT NULL,
    location TEXT NOT NULL,
    versions INTEGER,
    description TEXT 
);
'''

c_metadata = '''CREATE TABLE metadata(
    meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id INTEGER NOT NULL,
    uri TEXT, 
    repository TEXT NOT NULL,
    tool TEXT NOT NULL,
    provider TEXT NOT NULL,
    suite TEXT,
    method TEXT NOT NULL, 
    origin INTEGER NOT NULL, 
    docker_origin INTEGER NOT NULL,
    FOREIGN KEY (tool_id)
        REFERENCES tools (tool_id)
);'''

c_version_data = '''CREATE TABLE version_data(
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
        self.db_conn = sqlite3.connect(config.tool_db)
        self.cursor = self.db_conn.cursor()

    def configure(self):
        # Enable Foreign Keys
        self.cursor.execute("PRAGMA foreign_keys = ON")

    def create_metadata_table(self):
        self.cursor.execute(c_metadata)

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