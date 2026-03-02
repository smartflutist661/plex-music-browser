from flask.wrappers import Request

MAX_SORT_COLS = 3
SORT_COLS = (
    "track",
    "album",
    "artist",
    "rating",
    "track_count",
    "last_rated_at",
)


def build_sort(request: Request) -> str:
    # sort
    sorts = []
    for sort_col_num in range(MAX_SORT_COLS):
        sort_col_index = request.args.get(f"order[{sort_col_num}][column]")
        if sort_col_index is None and sort_col_num > 0:
            break
        sort_col_name = request.args.get(f"columns[{sort_col_index}][data]")
        # Specify allowed sort parameters to prevent SQL injection
        # Can't parameterize "order by"
        if sort_col_name not in SORT_COLS or sort_col_name == "artist":
            sort_col_name = "artist_sort"
        elif sort_col_name == "track":
            sort_col_name = "track_sort"
        elif sort_col_name == "album":
            sort_col_name = "album_sort"
        sort_direction = request.args.get(f"order[{sort_col_num}][dir]")
        if sort_direction not in ("asc", "desc"):
            sort_direction = "asc"
        sorts.append(f"{sort_col_name} {sort_direction}")
    return " order by " + ", ".join(sorts) + ";"
