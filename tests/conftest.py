import sqlite3
from collections.abc import Generator
from pathlib import Path
from sqlite3 import Connection

import pytest
from flask import Flask
from flask.testing import FlaskClient

from plex_music_browser import APP


@pytest.fixture(name="app", scope="session")
def app_fixture() -> Generator[Flask, None, None]:
    APP.config.update(
        {
            "TESTING": True,
        }
    )

    yield APP


@pytest.fixture(name="conn", scope="session")
def conn_fixture() -> Generator[Connection, None, None]:

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row

    for file in sorted((Path(__file__).parent / "sql_setup").iterdir()):
        with file.open(encoding="utf8") as sql_file:
            print(file)
            cur = db.cursor()
            cur.execute(sql_file.read())
            cur.close()

    yield db


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
