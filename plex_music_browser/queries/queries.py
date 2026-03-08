from datetime import date
from pathlib import Path
from sqlite3 import Cursor
from typing import (
    Literal,
    Optional,
    Type,
    cast,
    overload,
)

from flask.wrappers import Response

from plex_music_browser.models.album import Album
from plex_music_browser.models.artist import Artist
from plex_music_browser.models.track import Track
from plex_music_browser.search import (
    SearchColumn,
    SearchCriteria,
    build_search,
)
from plex_music_browser.sort import (
    SortCriteria,
    build_sort,
)

QueryType = Literal["tracks", "albums", "artists"]


def get_query_base(query_type: QueryType) -> str:
    with (Path(__file__).parent / f"{query_type}.sql").open(encoding="utf8") as query_file:
        return query_file.read()


@overload
def get_by_id(
    query_id: int,
    query_type: Literal["tracks"],
    db_cursor: Cursor,
) -> Optional[Track]: ...
@overload
def get_by_id(
    query_id: int,
    query_type: Literal["albums"],
    db_cursor: Cursor,
) -> Optional[Album]: ...
@overload
def get_by_id(
    query_id: int,
    query_type: Literal["artists"],
    db_cursor: Cursor,
) -> Optional[Artist]: ...


def get_by_id(
    query_id: int,
    query_type: QueryType,
    db_cursor: Cursor,
) -> Optional[Track | Album | Artist]:
    query = get_query_base(query_type)
    query += f" SELECT * from {query_type} where id = ?;"

    item = db_cursor.execute(query, [query_id]).fetchone()
    if item is None:
        return item

    if query_type == "tracks":
        return Track(**item)
    if query_type == "albums":
        return Album(**item)
    if query_type == "artists":
        return Artist(**item)


def get_base_query_params(
    query_type: QueryType,
    artist_id: Optional[int],
    album_id: Optional[int],
    unrated: Optional[bool],
) -> tuple[list[str], list[str | int | float | date]]:
    query_terms = []
    query_params: list[str | int | float | date] = []

    if artist_id is not None:
        if query_type == "artists":
            query_terms.append("id = ?")
            query_params.append(artist_id)
        else:
            query_terms.append("artist_id = ?")
            query_params.append(artist_id)

    if album_id is not None:
        if query_type == "albums":
            query_terms.append("id = ?")
            query_params.append(album_id)
        # elif query_type == "aritst":
        #     query_terms.append("? = ANY(serieses_ids)")
        #     query_params.append(album_id)
        else:
            query_terms.append("album_id = ?")
            query_params.append(album_id)

    # Ternary: None = all, True = unrated, False = rated
    if unrated is not None:
        if unrated is True:
            query_terms.append("rating is null")
        else:
            query_terms.append("rating is not null")

    return query_terms, query_params


def get_total(
    query_type: QueryType,
    db_cursor: Cursor,
    artist_id: Optional[int],
    album_id: Optional[int],
    unrated: Optional[bool],
) -> int | Response:
    query = get_query_base(query_type) + f" SELECT count(*) as total from {query_type}"

    query_terms, query_params = get_base_query_params(query_type, artist_id, album_id, unrated)

    if len(query_terms) > 0:
        query += " where " + " AND ".join(query_terms)

    total_res = db_cursor.execute(query + ";", query_params).fetchone()
    if total_res is not None:
        return int(total_res["total"])

    return Response(f"No {query_type} found", 404)


def get_items(
    search_criteria: SearchCriteria,
    sort_criteria: Optional[SortCriteria],
    query_type: QueryType,
    db_cursor: Cursor,
    artist_id: Optional[int],
    album_id: Optional[int],
    unrated: Optional[bool],
) -> list[Track] | list[Artist] | list[Album] | Response:

    query = get_query_base(query_type) + f" SELECT * from {query_type}"

    query_terms, query_params = get_base_query_params(query_type, artist_id, album_id, unrated)

    if query_type == "tracks":
        valid_columns = Track.__annotations__.keys()
        item_type: Type[Track | Artist | Album] = Track
    elif query_type == "artists":
        valid_columns = Artist.__annotations__.keys()
        item_type = Artist
    elif query_type == "albums":
        valid_columns = Album.__annotations__.keys()
        item_type = Album
    else:
        raise ValueError(f"Unrecognized query type {query_type}, unable to retrieve valid columns")

    search = build_search(search_criteria, {SearchColumn(col) for col in valid_columns})
    if isinstance(search, Response):
        return search

    if search is not None or len(query_terms) > 0:
        query += " where "

    if len(query_terms) > 0:
        query += "(" + " AND ".join(query_terms) + ")"

    if search is not None and len(query_terms) > 0:
        query += " AND ("

    if search is not None:
        search_string, search_params = search
        query += search_string
        query_params.extend(search_params)

    if search is not None and len(query_terms) > 0:
        query += ")"

    if sort_criteria is not None:
        query += build_sort(sort_criteria)
    else:
        query += ";"

    db_cursor.execute(query, query_params)

    items = db_cursor.fetchall()
    validated_items = cast(
        list[Track] | list[Artist] | list[Album],
        [item_type(**item) for item in items],
    )
    return validated_items
