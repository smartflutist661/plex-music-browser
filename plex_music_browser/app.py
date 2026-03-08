import json
import os
import sqlite3
from pathlib import Path
from sqlite3 import Connection
from typing import (
    Optional,
    cast,
)

from dotenv import load_dotenv
from flask import (
    Flask,
    g,
)
from flask.globals import request
from flask.templating import render_template
from flask.wrappers import Response

from plex_music_browser.models.album import Album
from plex_music_browser.models.datatable_request import (
    datatable_request_to_search_criteria,
    datatable_request_to_sort_criteria,
)
from plex_music_browser.models.datatable_responses import (
    AlbumsResponse,
    ArtistsResponse,
    TracksResponse,
)
from plex_music_browser.pagination import paginate
from plex_music_browser.queries.queries import (
    QueryType,
    get_by_id,
    get_items,
    get_total,
)
from plex_music_browser.search import (
    IntSearchParam,
    SearchColumn,
    SearchCondition,
    SearchCriteria,
    TwoParameterCriterion,
)

load_dotenv(Path(__file__).parents[1] / ".env")

LIBRARY_ID = int(os.environ["LIBRARY_ID"])

APP: Flask = Flask(__name__)


def get_db() -> Connection:
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(os.environ["DB_FILE"])
        db.row_factory = sqlite3.Row
    return db


@APP.teardown_appcontext
def close_connection(_: Optional[BaseException]) -> None:
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def get_bool_from_param(val: str) -> Optional[bool]:
    opt = json.loads(val.lower())
    if opt is None:
        return None
    return bool(opt)


@APP.route("/.well-known/acme-challenge/<token>")
def certbot(token: str) -> str:
    """
    Route to answer a challenge from certbot
    for Let's Encrypt SSL certficate creation/renewal
    """
    webroot = os.getenv("WEBROOT")
    if webroot is None:
        raise FileNotFoundError("WEBROOT not set in .env, unable to answer certbot challenge")

    with open(f"{webroot}/.well-known/acme-challenge/" + token, encoding="utf8") as token_file:
        return token_file.read()


@APP.route("/")
def index() -> str | Response:
    now = datetime.now()
    start_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_last_month = start_of_this_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)

    search_criteria = SearchCriteria(
        basic_search_string=None,
        advanced_search={
            "AND": [
                TwoParameterCriterion(
                    SearchColumn("last_rated_at"),
                    SearchCondition("between"),
                    IntSearchParam(int(start_of_last_month.timestamp())),
                    IntSearchParam(int(end_of_last_month.timestamp())),
                )
            ]
        },
    )
    cur = get_db().cursor()
    filtered_items = get_items(
        search_criteria,
        sort_criteria=None,
        query_type="albums",
        db_cursor=cur,
        artist_id=None,
        album_id=None,
        unrated=False,
    )
    cur.close()

    if isinstance(filtered_items, Response):
        return filtered_items

    return render_template("index.html", title="Home", plot="")


@APP.route("/tracks")
def tracks() -> str | Response:
    track_id = request.args.get("id", type=int)

    if track_id is None:
        return render_template(
            "tracks.html",
            title="Tracks",
            unrated=request.args.get("unrated", type=get_bool_from_param),
        )
    else:
        return Response("Single-track pages not implemented", 400)


@APP.route("/artists")
def artists() -> str | Response:
    artist_id = request.args.get("id", type=int)
    if artist_id is None:
        return render_template("artists.html", title="Artists")

    cur = get_db().cursor()
    artist_res = get_by_id(artist_id, "artists", cur)
    cur.close()

    if artist_res is None:
        return Response(f"Artist with id {artist_id} not found", 404)

    return render_template(
        "albums.html",
        title=artist_res.artist,
        album_id=None,
        artist_id=artist_id,
        unrated=request.args.get("unrated", type=get_bool_from_param),
    )


@APP.route("/albums")
def albums() -> str | Response:
    album_id = request.args.get("id", type=int)

    if album_id is None:
        return render_template("albums.html", title="Albums")

    cur = get_db().cursor()
    album_res = get_by_id(album_id, "albums", cur)
    cur.close()

    if album_res is None:
        return Response(f"Album with id {album_id} not found", 404)

    return render_template(
        "tracks.html",
        title=f"{album_res.album} by {album_res.artist}",
        album_id=album_id,
        artist_id=None,
        unrated=request.args.get("unrated", type=get_bool_from_param),
    )


# TODO: Cover collages for artists?
@APP.route("/api/datatables")
def data() -> TracksResponse | ArtistsResponse | AlbumsResponse | Response:

    query_type = cast(QueryType, request.args.get("query_type", type=str))
    artist_id = request.args.get("artist_id", type=int)
    album_id = request.args.get("album_id", type=int)
    unrated = request.args.get("unrated", type=get_bool_from_param)

    cur = get_db().cursor()
    total = get_total(query_type, cur, artist_id, album_id, unrated)
    if isinstance(total, Response):
        return total

    search_criteria = datatable_request_to_search_criteria(request)
    if isinstance(search_criteria, Response):
        return search_criteria
    sort_criteria = datatable_request_to_sort_criteria(request)
    filtered_items = get_items(
        search_criteria, sort_criteria, query_type, cur, artist_id, album_id, unrated
    )
    cur.close()

    if isinstance(filtered_items, Response):
        return filtered_items

    total_filtered = len(filtered_items)

    paginated_items = paginate(request, filtered_items)  # type: ignore[misc]

    # response
    return {
        "data": [item.model_dump() for item in paginated_items],
        "recordsFiltered": total_filtered,
        "recordsTotal": total,
        "draw": request.args.get("draw", type=int),
    }
