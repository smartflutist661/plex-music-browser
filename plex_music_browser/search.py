from collections.abc import (
    Iterable,
    Mapping,
)
from dataclasses import dataclass
from typing import (
    AbstractSet,
    Literal,
    NewType,
    Optional,
)

from flask.wrappers import Response

STRING_COLS = frozenset(
    {
        "track",
        "album",
        "artist",
        "genres",
        "styles",
    }
)
NUM_COLS = ("rating",)
DATE_COLS = ("last_rated_at",)

STRING_CONDITIONS = (
    "=",
    "!=",
    "starts",
    "!starts",
    "contains",
    "!contains",
    "ends",
    "!ends",
    "null",
    "!null",
)

NUM_CONDITIONS = (
    "=",
    "!=",
    "<",
    "<=",
    ">=",
    ">",
    "between",
    "!between",
    "null",
    "!null",
)
DATE_CONDITIONS = (
    "=",
    "!=",
    "<",
    ">",
    "between",
    "!between",
    "null",
    "!null",
)

SearchType = NewType("SearchType", str)
SearchColumn = NewType("SearchColumn", str)
SearchCondition = NewType("SearchCondition", str)
StringSearchParam = NewType("StringSearchParam", str)
IntSearchParam = NewType("IntSearchParam", int)
FloatSearchParam = NewType("FloatSearchParam", float)
SearchParam = StringSearchParam | IntSearchParam | FloatSearchParam


@dataclass
class OneParameterCriterion:
    column: SearchColumn
    condition: SearchCondition
    value: SearchParam


@dataclass
class TwoParameterCriterion:
    column: SearchColumn
    condition: SearchCondition
    left_value: SearchParam
    right_value: SearchParam


AdvancedSearch = Mapping[
    Literal["AND", "OR"],
    Iterable["OneParameterCriterion | TwoParameterCriterion | AdvancedSearch"],
]


@dataclass
class SearchCriteria:
    basic_search_string: Optional[str]
    advanced_search: Optional[AdvancedSearch]


def build_search(
    search_params: SearchCriteria,
    valid_columns: AbstractSet[SearchColumn],
) -> Optional[tuple[str, tuple[str | int | float, ...]] | Response]:

    # Build basic search string
    if search_params.basic_search_string is not None:
        res: tuple[str, tuple[str | float | int, ...]] | Response = build_basic_search(
            search_params.basic_search_string, valid_columns
        )
        if isinstance(res, Response):
            return res
        basic_search_string, basic_search_params = res

    if search_params.advanced_search is not None:
        # Build advanced search string
        res = build_advanced_search(search_params.advanced_search)
        if isinstance(res, Response):
            return res
        advanced_search_string, advanced_search_params = res

        # If successful, return, joining with basic search if necessary
        if res is not None:
            if search_params.basic_search_string is None:
                return advanced_search_string, advanced_search_params
            return (
                # local `basic_search_string` is guaranteed to be asssigned above if the param is not None
                # pylint: disable=possibly-used-before-assignment
                basic_search_string + " AND (" + advanced_search_string + ")",
                basic_search_params + advanced_search_params,
                # pylint: enable=possibly-used-before-assignment
            )

    # If advanced search could not be built,
    if search_params.basic_search_string is not None:
        return basic_search_string, basic_search_params

    return None


def build_advanced_search(
    advanced_search: AdvancedSearch,
) -> tuple[str, tuple[str | int | float, ...]] | Response:
    query_params: list[str | int | float] = []

    for logic, criteria in advanced_search.items():
        query_terms = []
        for criterion in criteria:
            if isinstance(criterion, OneParameterCriterion):
                query_terms.append(f"{criterion.column} {criterion.condition} ?")
                query_params.append(criterion.value)
            elif isinstance(criterion, TwoParameterCriterion):
                query_terms.append(f"{criterion.column} {criterion.condition} ? and ?")
                query_params.extend([criterion.left_value, criterion.right_value])
            else:  # if isinstance(criterion, AdvancedSearch):
                res = build_advanced_search(criterion)
                if isinstance(res, Response):
                    return res
                term, params = res
                query_terms.append(f"({term})")
                query_params.extend(params)

        # Should only be one logical operator at each level, return immediately
        return f" {logic} ".join(query_terms), tuple(query_params)

    # Shouldn't reach this
    return Response("Failed to build advanced search")


def build_basic_search(
    search_param: str,
    valid_columns: AbstractSet[str],
) -> tuple[str, tuple[str, ...]] | Response:
    search_strings = [f"%{search_string}%" for search_string in search_param.split()]
    total_search_strings = len(search_strings)
    if total_search_strings > 10:
        return Response("Too many search terms", 400)

    search_cols = valid_columns & STRING_COLS

    query = (
        "("
        + " OR ".join(
            sum(
                (
                    [f"lower({string_search_col}) like lower(?)"] * total_search_strings
                    for string_search_col in search_cols
                ),
                [],
            )
        )
        + ")"
    )
    query_params = search_strings * len(search_cols)
    return query, tuple(query_params)
