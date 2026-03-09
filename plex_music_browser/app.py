import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from sqlite3 import Connection
from typing import (
    Optional,
    cast,
)

import pandas
import plotly.express as px
from dotenv import load_dotenv
from flask import (
    Flask,
    g,
)
from flask.globals import request
from flask.templating import render_template
from flask.wrappers import Response

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
    OneParameterCriterion,
    SearchColumn,
    SearchCondition,
    SearchCriteria,
)
from plex_music_browser.sort import (
    SortColumn,
    SortCriteria,
    SortCriterion,
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
    webroot = os.getenv("WEBROOT", "/var/www/html")
    if webroot is None:
        raise FileNotFoundError("WEBROOT not set in .env, unable to answer certbot challenge")

    with open(f"{webroot}/.well-known/acme-challenge/" + token, encoding="utf8") as token_file:
        return token_file.read()


def generate_plots() -> str | Response:
    this_year = datetime.today().year
    start_time = datetime(this_year, 1, 1)

    search_criteria = SearchCriteria(
        basic_search_string=None,
        advanced_search={
            "AND": [
                OneParameterCriterion(
                    SearchColumn("last_rated_at"),
                    SearchCondition(">"),
                    IntSearchParam(int(start_time.timestamp())),
                )
            ]
        },
    )
    cur = get_db().cursor()
    filtered_items = get_items(
        search_criteria,
        sort_criteria=SortCriteria([SortCriterion(SortColumn("last_rated_at"), "asc")]),
        query_type="albums",
        db_cursor=cur,
        artist_id=None,
        album_id=None,
        unrated=False,
    )
    cur.close()

    if isinstance(filtered_items, Response):
        return filtered_items

    albums_df = pandas.DataFrame(item.model_dump() for item in filtered_items)
    albums_df["month"] = albums_df["last_rated_at"].dt.strftime("%b")
    grouped_by_month = (
        albums_df.groupby(by=["month", "rating"])
        .agg(
            count=pandas.NamedAgg(column="album", aggfunc="count"),
        )
        .reset_index()
    )
    grouped_by_month["rating"] = grouped_by_month["rating"].astype(str)

    # TODO: Add avg rating line plot overlay?
    # TODO: Better color
    fig1 = px.bar(
        grouped_by_month,
        title="Albums rated by month",
        x="month",
        y="count",
        color="rating",
        template="seaborn+presentation",  # type: ignore[arg-type] # presentation is an add-on
        category_orders={
            "month": [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "June",
                "July",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
        },
        # hover_data="album",
    )
    # TODO: Loop through raw table grouped by month to create tabs(?) with datatable each
    # TODO: Table by genre
    return fig1.to_html(full_html=False, include_plotlyjs=False)


@APP.route("/")
def index() -> str | Response:
    plots = generate_plots()
    if isinstance(plots, Response):
        return plots
    return render_template("index.html", title="Home", plot=plots)


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
