from sqlite3 import Connection

from flask import Flask

from plex_music_browser.queries.queries import get_items

# TODO: Test a bunch of Ajax requests
# TODO: Test expected values by ID


def test_all_tracks(app: Flask, conn: Connection) -> None:
    with app.test_request_context() as mock_context:
        items = get_items(
            mock_context.request,
            "tracks",
            conn.cursor(),
            author_id=None,
            series_id=None,
            unrated=None,
        )
    assert isinstance(items, list)
    assert len(items) == 9


def test_all_artists(app: Flask, conn: Connection) -> None:
    with app.test_request_context() as mock_context:
        items = get_items(
            mock_context.request,
            "artists",
            conn.cursor(),
            author_id=None,
            series_id=None,
            unrated=None,
        )
    assert isinstance(items, list)
    assert len(items) == 3


def test_all_albums(app: Flask, conn: Connection) -> None:
    with app.test_request_context() as mock_context:
        items = get_items(
            mock_context.request,
            "albums",
            conn.cursor(),
            author_id=None,
            series_id=None,
            unrated=None,
        )
    assert isinstance(items, list)
    assert len(items) == 3
