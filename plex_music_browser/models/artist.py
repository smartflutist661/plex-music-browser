from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    field_validator,
)


class Artist(BaseModel):
    id: int
    artist: str
    artist_sort: str
    rating: Optional[int]
    last_rated_at: Optional[datetime]
    genres: list[str]
    styles: list[str]

    @field_validator("genres", "styles", mode="plain")
    @classmethod
    def split_list(cls, data: Optional[str]) -> list[str]:
        if data is None or len(data) == 0:
            return []
        return str(data).split("|")
