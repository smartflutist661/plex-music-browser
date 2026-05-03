from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Optional,
)

from pydantic import (
    BaseModel,
    field_serializer,
    field_validator,
)


class Album(BaseModel):
    id: int
    album: str
    album_sort: str
    artist_id: int
    artist: str
    artist_sort: str
    rating: Optional[int]
    last_rated_at: Optional[datetime]
    genres: list[str]
    styles: list[str]
    length: timedelta
    avg_track_rating: Optional[float]

    @field_validator("genres", "styles", mode="plain")
    @classmethod
    def split_list(cls, data: Optional[str]) -> list[str]:
        if data is None or len(data) == 0:
            return []
        return str(data).split("|")

    @field_serializer("last_rated_at")
    def serialize_dt(self, dt: Optional[datetime], _: Any) -> Optional[int]:
        if dt is None:
            return None
        return int(dt.timestamp() * 1000)

    @field_serializer("length")
    def serialize_td(self, td: timedelta, _: Any) -> int:
        return int(td.total_seconds() * 1000)

    @field_validator("length", mode="before")
    @classmethod
    def deserialize_td(cls, val: int) -> timedelta:
        return timedelta(milliseconds=val)
