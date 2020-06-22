import sqlite3


class Database:

    def __init__(self):
        conn = sqlite3.connect("tool_information.db")
