from typing import TypeVar

from flask.wrappers import Request

T = TypeVar("T")


def paginate(request: Request, query_res: list[T]) -> list[T]:
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    if start is None:
        start = 0
    if length is None:
        return query_res[start:]
    return query_res[start : start + length]
