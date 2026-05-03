import math
from collections import defaultdict
from collections.abc import (
    Collection,
    Iterable,
    Mapping,
)
from datetime import datetime
from typing import TypedDict

import numpy
import pandas
import plotly.graph_objects as go
import tzlocal
from flask import (
    Response,
    render_template,
)
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


class MonthDataCache(TypedDict):
    last_seen_count: int
    month_data: dict[str, list[Album]]


MONTH_DATA: MonthDataCache = {"last_seen_count": 0, "month_data": {}}


def populate_month_data(rated_albums: Collection[Album]) -> None:
    month_data = defaultdict(list)
    for album in rated_albums:
        assert album.last_rated_at is not None
        month_data[album.last_rated_at.strftime("%b")].append(album)
    MONTH_DATA["month_data"] = month_data
    MONTH_DATA["last_seen_count"] = len(rated_albums)


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


def generate_summary_plot(month_rating_df: pandas.DataFrame) -> str:
    grouped_by_month = (
        month_rating_df.groupby(by=["month"])
        .apply(lambda df: (df["count"] * df["rating"]).sum() / df["count"].sum())
        .rename("avg_rating")
        .reset_index()
        .sort_values("month", key=lambda vals: vals.map(MONTH_ORDER_MAP))
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    color_points = numpy.linspace(0, 1, 10)
    colors = sample_colorscale("RdYlGn", color_points)
    for rating, rating_df in month_rating_df.groupby("rating"):
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
        margin={"l": 0, "r": 0},
        title_xanchor="center",
        title_x=0.48,
        barmode="stack",
        xaxis={
            "categoryorder": "array",
            "categoryarray": MONTH_ORDER,
        },
        legend={
            "orientation": "h",
            "y": -0.2,
            "yanchor": "top",
            "xanchor": "center",
            "x": 0.5,
            "traceorder": "normal",
            # "entrywidth": 80,
        },
    )
    fig.update_xaxes(
        title_text="Month",
    )
    max_ratings = math.ceil(month_rating_df.groupby(by=["month"])["count"].sum().max() / 10) * 10
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

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_month_tabs() -> str:
    tabs = '<div class="tab">'
    tab_content = ""

    available_months = sorted(
        MONTH_DATA["month_data"].keys(), key=lambda month: MONTH_ORDER_MAP[month]
    )
    for month in available_months:
        tab_data = render_template(
            "month_stats_tab.html",
            month=month,
        )
        # For the current month, start the tab active
        if month == available_months[-1]:
            tabs += f"""<button class="tablink active" onclick="openMonth(event, '{month}')">{month}</button>"""
            tab_content += f"""
            <div id="{month}" class="tabcontent" style="display: block;">
                {tab_data}
            </div>
            """
        else:
            tabs += f"""<button class="tablink" onclick="openMonth(event, '{month}')">{month}</button>"""
            tab_content += f"""
            <div id="{month}" class="tabcontent" style="display: none;">
                {tab_data}
            </div>
            """
    tabs += "</div>"

    return tabs + "\n" + tab_content


def generate_stats_page() -> str | Response:
    rated_albums = get_albums_rated_this_year()
    if isinstance(rated_albums, Response):
        return rated_albums

    # Refresh album data if count is different
    # Highly unlikely to be a case where this count remains the same because of new ratings + deletions
    if MONTH_DATA["last_seen_count"] != len(rated_albums):
        populate_month_data(rated_albums)

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

    total_by_month = (
        grouped_by_month_and_rating.groupby(by=["month"])["count"]
        .sum()
        .rename("total_by_month")
        .reset_index()
    )
    grouped_by_month_and_rating = grouped_by_month_and_rating.merge(total_by_month, on="month")

    fig_html = generate_summary_plot(grouped_by_month_and_rating)
    tab_html = generate_month_tabs()
    final_html = "\n".join(
        [fig_html, '<h1 style="text-align: center;">Rated albums</h1>', tab_html]
    )
    # TODO: Stats by genres/styles
    # TODO: Stats by artist
    # TODO: Include total times for albums? artists? months (in summary plot somehow)?
    # TODO: Include average track ratings for albums? artists?
    return final_html
