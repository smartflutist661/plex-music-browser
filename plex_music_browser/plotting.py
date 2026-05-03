import math
from collections import defaultdict
from collections.abc import (
    Collection,
    Iterable,
    Mapping,
)
from datetime import (
    datetime,
    timedelta,
)
from itertools import (
    cycle,
    islice,
)
from typing import (
    TypedDict,
    cast,
)
from zoneinfo import ZoneInfo

import numpy
import pandas
import plotly
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

LOCAL_TZ = tzlocal.get_localzone_name()


def populate_month_data(rated_albums: Collection[Album]) -> None:
    month_data = defaultdict(list)
    for album in rated_albums:
        assert album.last_rated_at is not None
        month_data[album.last_rated_at.astimezone(ZoneInfo(LOCAL_TZ)).strftime("%b")].append(album)
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


def generate_album_summary_plot(albums_df: pandas.DataFrame) -> str:
    grouped_by_month_and_rating = (
        albums_df.groupby(by=["month", "rating"])
        .agg(
            count=pandas.NamedAgg(column="album", aggfunc="count"),
            total_time=pandas.NamedAgg(column="duration", aggfunc="sum"),
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

    grouped_by_month = (
        grouped_by_month_and_rating.groupby(by=["month"])
        .apply(lambda df: (df["count"] * df["rating"]).sum() / df["count"].sum())
        .rename("avg_rating")
        .reset_index()
        .sort_values("month", key=lambda vals: vals.map(MONTH_ORDER_MAP))
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    color_points = numpy.linspace(0, 1, 10)
    colors = sample_colorscale("RdYlGn", color_points)
    max_rating_by_month = grouped_by_month_and_rating.groupby("month")["rating"].max()
    total_time_by_month = grouped_by_month_and_rating.groupby("month")["total_time"].sum()
    for rating, rating_df in grouped_by_month_and_rating.groupby("rating"):
        assert isinstance(rating, int), "Rating column is not an integer"
        text = [
            (
                format_timedelta(total_time_by_month[month])
                if rating == max_rating_by_month[month]
                else None
            )
            for month in rating_df["month"].to_list()
        ]
        color = colors[rating - 1]
        fig.add_trace(
            go.Bar(
                x=rating_df["month"],
                y=rating_df["count"],
                text=cast(list[str], text),  # Lie
                textposition="outside",
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
        },
    )
    fig.update_xaxes(
        title_text="Month",
    )
    max_ratings = (
        math.ceil(grouped_by_month_and_rating.groupby(by=["month"])["count"].sum().max() / 10) * 10
    )
    max_ratings = math.ceil(max_ratings * 1.025)
    step = round((max_ratings // 10) / 5) * 5
    ticks1 = list(range(0, max_ratings, step))
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


def format_timedelta(td: timedelta) -> str:
    time_strs = []
    secs = td.total_seconds()

    days = math.floor(secs / (60 * 60 * 24))
    hours = math.floor(secs / (60 * 60) % 24)
    minutes = 0
    seconds = 0
    if days != 0:
        time_strs.append(f"{days}d")
    if hours != 0:
        time_strs.append(f"{hours}h")
    if days == 0:
        minutes = math.floor(secs / 60 % 60)
        if minutes != 0:
            time_strs.append(f"{minutes}m")
    if hours == 0:
        seconds = math.floor(secs % 60)
        if seconds != 0:
            time_strs.append(f"{seconds}s")

    return " ".join(time_strs)


def generate_month_summary_plot(df: pandas.DataFrame, col: str, title: str) -> str:
    df.sort_values(by=["count", "avg_rating", col], inplace=True)
    plot_height = 150 + (len(df) * 20)

    colors = list(islice(cycle(plotly.express.colors.qualitative.Plotly), len(df)))

    fig = make_subplots(cols=2, shared_yaxes=True, horizontal_spacing=0.01)
    fig.add_trace(
        go.Bar(
            x=df["count"],
            y=df[col],
            text=[format_timedelta(time) for time in df["total_time"].to_list()],
            textposition="outside",
            marker_color=colors,
            name="Rated Albums",
            orientation="h",
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=df["avg_rating"],
            y=df[col],
            marker_color=colors,
            name="Average Rating",
            orientation="h",
            hovertemplate="%{x:.2f}<extra></extra>",
        ),
        row=1,
        col=2,
    )
    fig.update_layout(
        height=plot_height,
        showlegend=False,
    )
    fig.update_xaxes(side="top")
    fig.update_xaxes(
        title_text=title,
        range=[0, df["count"].max() * 1.1],
        row=1,
        col=1,
    )
    fig.update_xaxes(title_text="Average Rating", row=1, col=2)
    fig.update_yaxes(
        dtick=1,
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_month_tabs(albums_df: pandas.DataFrame) -> str:
    tabs = '<div class="tab">'
    tab_content = ""

    available_months = sorted(
        MONTH_DATA["month_data"].keys(), key=lambda month: MONTH_ORDER_MAP[month]
    )
    artist_df = (
        albums_df.groupby(by=["month", "artist"])
        .agg(
            count=pandas.NamedAgg(column="album", aggfunc="count"),
            avg_rating=pandas.NamedAgg(column="rating", aggfunc="mean"),
            total_time=pandas.NamedAgg(column="duration", aggfunc="sum"),
        )
        .reset_index()
    )
    style_df = (
        albums_df.explode("styles")
        .groupby(by=["month", "styles"])
        .agg(
            count=pandas.NamedAgg(column="album", aggfunc="count"),
            avg_rating=pandas.NamedAgg(column="rating", aggfunc="mean"),
            total_time=pandas.NamedAgg(column="duration", aggfunc="sum"),
        )
        .reset_index()
    )
    for month in available_months:
        artist_summary_html = generate_month_summary_plot(
            artist_df[artist_df["month"] == month], "artist", "# Albums Rated Per Artist"
        )
        style_summary_html = generate_month_summary_plot(
            style_df[style_df["month"] == month], "styles", "# Albums Rated Per Style"
        )
        tab_data = "\n".join(
            [
                artist_summary_html,
                style_summary_html,
                render_template(
                    "month_stats_tab.html",
                    month=month,
                ),
            ]
        )
        # For the current month, start the tab active
        if month == available_months[-1]:
            tabs += f"""<button data-month="{month}" class="tablink active" onclick="openMonth(event, '{month}')">{month}</button>"""
            tab_content += f"""
            <div id="{month}" class="tabcontent" style="display: block;">
                {tab_data}
            </div>
            """
        else:
            tabs += f"""<button data-month="{month}" class="tablink" onclick="openMonth(event, '{month}')">{month}</button>"""
            tab_content += f"""
            <div id="{month}" class="tabcontent" style="display: block;">
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
    albums_df["month"] = (
        pandas.to_datetime(albums_df["last_rated_at"], unit="ms")
        .dt.tz_localize("UTC")
        .dt.tz_convert(LOCAL_TZ)
        .dt.strftime("%b")
    )
    albums_df["duration"] = pandas.to_timedelta(albums_df["length"], unit="ms").dt.to_pytimedelta()

    album_summary_html = generate_album_summary_plot(albums_df)
    tab_html = generate_month_tabs(albums_df)
    final_html = "\n".join(
        [
            album_summary_html,
            tab_html,
        ]
    )
    return final_html
