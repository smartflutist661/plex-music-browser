from collections.abc import Iterable
from dataclasses import dataclass
from typing import (
    Literal,
    NewType,
)

MAX_SORT_COLS = 3
SORT_COLS = (
    "track",
    "album",
    "artist",
    "rating",
    "track_count",
    "last_rated_at",
)

SortColumn = NewType("SortColumn", str)
SortDirection = Literal["asc", "desc"]


@dataclass
class SortCriterion:
    column: SortColumn
    direction: SortDirection


@dataclass
class SortCriteria:
    sorts: Iterable[SortCriterion]


def build_sort(sort_criteria: SortCriteria) -> str:
    sorts = []
    for sort in sort_criteria.sorts:
        sorts.append(f"{sort.column} {sort.direction}")
    return " order by " + ", ".join(sorts) + ";"
