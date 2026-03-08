from sqlite3 import Connection

from flask import (
    Flask,
    Response,
)

from plex_music_browser.models.datatable_request import (
    datatable_request_to_search_criteria,
    datatable_request_to_sort_criteria,
)
from plex_music_browser.queries.queries import get_items

# TODO: Test a bunch of Ajax requests
# TODO: Test expected values by ID


def test_all_tracks(app: Flask, conn: Connection) -> None:
    with app.test_request_context() as mock_context:
        search_criteria = datatable_request_to_search_criteria(mock_context.request)
        if isinstance(search_criteria, Response):
            raise ValueError(Response)
        sort_criteria = datatable_request_to_sort_criteria(mock_context.request)
        items = get_items(
            search_criteria,
            sort_criteria,
            "tracks",
            conn.cursor(),
            artist_id=None,
            album_id=None,
            unrated=None,
        )
    assert isinstance(items, list)
    assert len(items) == 9


def test_all_artists(app: Flask, conn: Connection) -> None:
    with app.test_request_context() as mock_context:
        search_criteria = datatable_request_to_search_criteria(mock_context.request)
        if isinstance(search_criteria, Response):
            raise ValueError(Response)
        sort_criteria = datatable_request_to_sort_criteria(mock_context.request)
        items = get_items(
            search_criteria,
            sort_criteria,
            "artists",
            conn.cursor(),
            artist_id=None,
            album_id=None,
            unrated=None,
        )
    assert isinstance(items, list)
    assert len(items) == 3


def test_all_albums(app: Flask, conn: Connection) -> None:
    with app.test_request_context() as mock_context:
        search_criteria = datatable_request_to_search_criteria(mock_context.request)
        if isinstance(search_criteria, Response):
            raise ValueError(Response)
        sort_criteria = datatable_request_to_sort_criteria(mock_context.request)
        items = get_items(
            search_criteria,
            sort_criteria,
            "albums",
            conn.cursor(),
            artist_id=None,
            album_id=None,
            unrated=None,
        )
    assert isinstance(items, list)
    assert len(items) == 3
