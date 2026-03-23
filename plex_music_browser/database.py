import os
import sqlite3
from sqlite3 import Connection

from flask import g


def get_db() -> Connection:
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(os.environ["DB_FILE"])
        db.row_factory = sqlite3.Row
    return db
