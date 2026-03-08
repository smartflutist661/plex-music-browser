from datetime import (
    date,
    datetime,
    timedelta,
)
from typing import (
    Literal,
    Optional,
)

from flask import (
    Request,
    Response,
)

from plex_music_browser.search import (
    DATE_COLS,
    DATE_CONDITIONS,
    NUM_COLS,
    NUM_CONDITIONS,
    STRING_COLS,
    STRING_CONDITIONS,
    AdvancedSearch,
    FloatSearchParam,
    IntSearchParam,
    OneParameterCriterion,
    SearchColumn,
    SearchCondition,
    SearchCriteria,
    SearchType,
    StringSearchParam,
    TwoParameterCriterion,
)
from plex_music_browser.sort import (
    MAX_SORT_COLS,
    SORT_COLS,
    SortColumn,
    SortCriteria,
    SortCriterion,
)


###################
# Search
###################
def extract_criterion(
    request: Request,
    criterion_base: str,
) -> Optional[OneParameterCriterion | TwoParameterCriterion | AdvancedSearch]:

    # First validate request column and condition
    criterion_type = request.args.get(f"{criterion_base}[type]", type=SearchType)
    if criterion_type is None:
        return None
    criterion_col = request.args.get(f"{criterion_base}[origData]", type=SearchColumn)
    criterion_cond = request.args.get(f"{criterion_base}[condition]", type=SearchCondition)

    if not (
        (
            criterion_type == "string"
            and criterion_col in STRING_COLS
            and criterion_cond in STRING_CONDITIONS
        )
        or (
            criterion_type == "num"
            and criterion_col in NUM_COLS
            and criterion_cond in NUM_CONDITIONS
        )
        or (
            criterion_type == "date"
            and criterion_col in DATE_COLS
            and criterion_cond in DATE_CONDITIONS
        )
    ):
        return None

    # Then extract SQL query info based on condition and type
    criterion_val: Optional[str | int | float | date] = None
    criterion_val_1: Optional[str | int | float | date] = None
    criterion_val_2: Optional[str | int | float | date] = None
    if criterion_cond in ("=", "!=", "<", "<=", ">", ">="):
        if criterion_type == "num":
            criterion_val = request.args.get(f"{criterion_base}[value1]", type=float)
            if criterion_val is not None:
                return OneParameterCriterion(
                    criterion_col, criterion_cond, FloatSearchParam(criterion_val)
                )

        if criterion_type == "string":
            criterion_val = request.args.get(f"{criterion_base}[value1]", type=str)
            if criterion_val is not None:
                return OneParameterCriterion(
                    criterion_col, criterion_cond, StringSearchParam(criterion_val)
                )

        if criterion_type == "date":
            criterion_val = request.args.get(
                f"{criterion_base}[value1]", type=datetime.fromisoformat
            )
            if criterion_val is not None:
                # Dates are compared to midnight here
                if criterion_cond in ("<", ">"):
                    if criterion_cond == ">":
                        criterion_val += timedelta(days=1)
                    return OneParameterCriterion(
                        criterion_col,
                        criterion_cond,
                        IntSearchParam(int(criterion_val.timestamp())),
                    )

                if criterion_cond == "=":
                    criterion_val_1 = int(criterion_val.timestamp())
                    criterion_val_2 = int((criterion_val + timedelta(days=1)).timestamp())
                    criterion_cond = SearchCondition("between")
                else:  # if criterion_cond == "!=":
                    criterion_val_1 = int(criterion_val.timestamp())
                    criterion_val_2 = int((criterion_val + timedelta(days=1)).timestamp())
                    criterion_cond = SearchCondition("not between")

                return TwoParameterCriterion(
                    criterion_col,
                    criterion_cond,
                    IntSearchParam(criterion_val_1),
                    IntSearchParam(criterion_val_2),
                )

    if criterion_cond in ("null", "!null"):
        if criterion_type == "string":
            param_1 = StringSearchParam("null")
            param_2 = StringSearchParam("''")
            if "!" in criterion_cond:
                logic: Literal["AND", "OR"] = "AND"
                condition_1 = SearchCondition("is not")
                condition_2 = SearchCondition("!=")
            else:
                logic = "OR"
                condition_1 = SearchCondition("is")
                condition_2 = SearchCondition("=")

            return {
                logic: [
                    OneParameterCriterion(criterion_col, condition_1, param_1),
                    OneParameterCriterion(criterion_col, condition_2, param_2),
                ]
            }

        if criterion_type in ("num", "date"):
            if "!" in criterion_cond:
                return OneParameterCriterion(
                    criterion_col, SearchCondition("is not"), StringSearchParam("null")
                )
            return OneParameterCriterion(
                criterion_col, SearchCondition("is"), StringSearchParam("null")
            )

    if (
        criterion_cond in ("starts", "!starts", "contains", "!contains", "ends", "!ends")
        and criterion_type == "string"
    ):
        criterion_val = request.args.get(f"{criterion_base}[value1]", type=str)
        if criterion_val is not None:
            criterion_col = SearchColumn(f"lower({criterion_col})")
            if "!" in criterion_cond:
                criterion_cond = SearchCondition("not like")
            else:
                criterion_cond = SearchCondition("like")

            if "starts" in criterion_cond:
                criterion_val = StringSearchParam(f"{criterion_val.lower()}%")
            elif "ends" in criterion_cond:
                criterion_val = StringSearchParam(f"%{criterion_val.lower()}")
            elif "contains" in criterion_cond:
                criterion_val = StringSearchParam(f"%{criterion_val.lower()}%")
            else:
                raise ValueError("Invalid string condition in advanced search")

            return OneParameterCriterion(criterion_col, criterion_cond, criterion_val)

    if criterion_cond in ("between", "!between"):
        if criterion_type == "num":
            criterion_val_1 = request.args.get(f"{criterion_base}[value1]", type=int)
            criterion_val_2 = request.args.get(f"{criterion_base}[value2]", type=int)
        else:
            criterion_val_1 = request.args.get(
                f"{criterion_base}[value1]",
                type=lambda val: int(datetime.fromisoformat(val).timestamp()),
            )
            criterion_val_2 = request.args.get(
                f"{criterion_base}[value2]",
                type=lambda val: int(
                    (datetime.fromisoformat(val) - timedelta(days=1)).timestamp()
                ),
            )

        if criterion_val_1 is not None and criterion_val_2 is not None:
            if "!" in criterion_cond:
                criterion_cond = SearchCondition("not between")
            else:
                criterion_cond = SearchCondition("between")

            return TwoParameterCriterion(
                criterion_col,
                criterion_cond,
                IntSearchParam(criterion_val_1),
                IntSearchParam(criterion_val_2),
            )

    return None


def extract_advanced_search(
    request: Request,
    base_param: str,
    join_logic: Literal["AND", "OR"],
) -> AdvancedSearch:
    out_list: list[OneParameterCriterion | TwoParameterCriterion | AdvancedSearch] = []
    out_dict: AdvancedSearch = {join_logic: out_list}

    for criterion_num in range(10):
        criterion_base = f"{base_param}[{criterion_num}]"
        nested_logic = request.args.get(f"{criterion_base}[logic]")

        if nested_logic in ("AND", "OR"):
            out_list.append(
                extract_advanced_search(
                    request,
                    f"{criterion_base}[criteria]",
                    nested_logic,  # type: ignore[arg-type]  # validated in condition
                )
            )
        else:
            criterion = extract_criterion(request, criterion_base)
            if criterion is None:
                break
            out_list.append(criterion)

    return out_dict


def datatable_request_to_search_criteria(request: Request) -> SearchCriteria | Response:
    basic_search_param = request.args.get("search[value]")
    if basic_search_param == "":
        basic_search_param = None

    total_searchbuilder_criteria = len(
        [
            param
            for param in request.args.keys()
            if "searchBuilder" in param and "condition" in param
        ]
    )
    if total_searchbuilder_criteria > 10:
        return Response("Too many search criteria", 400)

    search_builder_outer_logic = request.args.get("searchBuilder[logic]")
    # Validate outer logic
    if search_builder_outer_logic not in ("AND", "OR"):
        search_builder_outer_logic = None

    advanced_search = None
    if search_builder_outer_logic is not None:
        advanced_search = extract_advanced_search(
            request,
            "searchBuilder[criteria]",
            search_builder_outer_logic,  # type: ignore[arg-type]  # validated above
        )

    return SearchCriteria(basic_search_param, advanced_search)


###############
# Sort
###############
def datatable_request_to_sort_criteria(request: Request) -> SortCriteria:
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
        elif sort_col_name == "album":
            sort_col_name = "album_sort"
        elif sort_col_name == "track":
            sort_col_name = "track_sort"

        sort_direction = request.args.get(f"order[{sort_col_num}][dir]")
        if sort_direction not in ("asc", "desc"):
            sort_direction = "asc"

        sorts.append(SortCriterion(SortColumn(sort_col_name), sort_direction))  # type: ignore[arg-type]  # validated above
    return SortCriteria(sorts)
