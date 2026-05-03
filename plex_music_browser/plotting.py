import math
from collections.abc import (
    Iterable,
    Mapping,
)
from datetime import datetime

import numpy
import pandas
import plotly.graph_objects as go
import tzlocal
from flask import Response
from plotly.express.colors import sample_colorscale
from plotly.subplots import make_subplots

from plex_music_browser.database import get_db
from plex_music_browser.models.album import Album
from plex_music_browser.queries.queries import get_items
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

MONTH_ORDER: Iterable[str] = [
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

MONTH_ORDER_MAP: Mapping[str, int] = {
    month: i
    for i, month in enumerate(
        [
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
    )
}


def get_albums_rated_this_year() -> list[Album] | Response:
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
        db_cursor=cur,
        artist_id=None,
        album_id=None,
        unrated=False,
        query_type="albums",
    )
    cur.close()

    return filtered_items


def generate_plots() -> str | Response:

    rated_albums = get_albums_rated_this_year()
    if isinstance(rated_albums, Response):
        return rated_albums

    albums_df = pandas.DataFrame(item.model_dump() for item in rated_albums)
    local_tz = tzlocal.get_localzone_name()
    albums_df["month"] = (
        pandas.to_datetime(albums_df["last_rated_at"], unit="ms")
        .dt.tz_localize("UTC")
        .dt.tz_convert(local_tz)
        .dt.strftime("%b")
    )

    grouped_by_month_and_rating = (
        albums_df.groupby(by=["month", "rating"])
        .agg(
            count=pandas.NamedAgg(column="album", aggfunc="count"),
        )
        .reset_index()
        .sort_values("rating")
    )

    grouped_by_month = (
        grouped_by_month_and_rating.groupby(by=["month"])
        .apply(lambda df: (df["count"] * df["rating"]).sum() / df["count"].sum())
        .rename("avg_rating")
        .reset_index()
        .sort_values("month", key=lambda vals: vals.map(MONTH_ORDER_MAP))
    )

    total_by_month = (
        grouped_by_month_and_rating.groupby(by=["month"])["count"]
        .sum()
        .rename("total_by_month")
        .reset_index()
    )
    grouped_by_month_and_rating = grouped_by_month_and_rating.merge(total_by_month, on="month")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    color_points = numpy.linspace(0, 1, 10)
    colors = sample_colorscale("RdYlGn", color_points)
    for rating, rating_df in grouped_by_month_and_rating.groupby("rating"):
        assert isinstance(rating, int), "Rating column is not an integer"
        color = colors[rating - 1]
        fig.add_trace(
            go.Bar(
                x=rating_df["month"],
                y=rating_df["count"],
                marker_color=color,
                name=f"{rating/2}★ Albums",
                customdata=rating_df["total_by_month"],
                hovertemplate="%{y}/%{customdata}",
            ),
            secondary_y=False,
        )
    fig.add_trace(
        go.Scatter(
            x=grouped_by_month["month"],
            y=grouped_by_month["avg_rating"],
            marker_color="black",
            name="Average Rating",
            hovertemplate="%{y:.2f}",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title_text="Albums rated by month",
        title_x=0.45,
        barmode="stack",
        xaxis={
            "categoryorder": "array",
            "categoryarray": MONTH_ORDER,
        },
    )
    fig.update_xaxes(
        title_text="Month",
    )
    max_ratings = (
        math.ceil(grouped_by_month_and_rating.groupby(by=["month"])["count"].sum().max() / 10) * 10
    )
    step = round((max_ratings // 8) / 5) * 5
    ticks1 = [tick for tick in range(0, max_ratings, step)[0:-1]] + [max_ratings]
    ticks2 = [tick / max_ratings * 10 for tick in ticks1]
    fig.update_yaxes(
        title_text="Albums Rated",
        tickmode="array",
        tickvals=ticks1,
        range=[0, max_ratings],
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Average Album Rating",
        range=[0, 10],
        tickmode="array",
        tickvals=ticks2,
        ticktext=[round(tick, 2) for tick in ticks2],
        secondary_y=True,
    )
    # TODO: Loop through raw table grouped by month to create tabs(?) with datatable each
    # TODO: Table with genres/styles
    # TODO: Stats by artist
    # TODO: Include total times
    # TODO: Include average track ratings
    return fig.to_html(full_html=False, include_plotlyjs=False)
