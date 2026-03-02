from sqlite3 import Connection

from plex_music_browser.queries.queries import get_total


def test_tracks_total(conn: Connection) -> None:
    assert get_total("tracks", conn.cursor(), artist_id=None, album_id=None, unrated=None) == 9


def test_author_tracks_total(conn: Connection) -> None:
    assert get_total("tracks", conn.cursor(), artist_id=1, album_id=None, unrated=None) == 5
    assert get_total("tracks", conn.cursor(), artist_id=2, album_id=None, unrated=None) == 4
    assert get_total("tracks", conn.cursor(), artist_id=3, album_id=None, unrated=None) == 0


def test_artists_total(conn: Connection) -> None:
    assert get_total("artists", conn.cursor(), artist_id=None, album_id=None, unrated=None) == 3
    assert get_total("artists", conn.cursor(), artist_id=1, album_id=None, unrated=None) == 1
    assert get_total("artists", conn.cursor(), artist_id=2, album_id=None, unrated=None) == 1
    assert get_total("artists", conn.cursor(), artist_id=3, album_id=None, unrated=None) == 1


# This page does not exist
def test_artist_albums_total(conn: Connection) -> None:
    assert get_total("albums", conn.cursor(), artist_id=1, album_id=None, unrated=None) == 2
    assert get_total("albums", conn.cursor(), artist_id=2, album_id=None, unrated=None) == 1
    assert get_total("albums", conn.cursor(), artist_id=3, album_id=None, unrated=None) == 0


def test_albums_tracks_total(conn: Connection) -> None:
    assert get_total("tracks", conn.cursor(), artist_id=None, album_id=4, unrated=None) == 2
    assert get_total("tracks", conn.cursor(), artist_id=None, album_id=5, unrated=None) == 3
    assert get_total("tracks", conn.cursor(), artist_id=None, album_id=6, unrated=None) == 4


def test_albums_total(conn: Connection) -> None:
    assert get_total("albums", conn.cursor(), artist_id=None, album_id=None, unrated=None) == 3
    assert get_total("albums", conn.cursor(), artist_id=None, album_id=4, unrated=None) == 1
    assert get_total("albums", conn.cursor(), artist_id=None, album_id=5, unrated=None) == 1
    assert get_total("albums", conn.cursor(), artist_id=None, album_id=6, unrated=None) == 1
