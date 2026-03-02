from typing import (
    Generic,
    Optional,
    TypedDict,
    TypeVar,
)

from plex_music_browser.models.album import Album
from plex_music_browser.models.artist import Artist
from plex_music_browser.models.track import Track

T = TypeVar("T")


class DataTableResponse(Generic[T], TypedDict):
    data: list[T]
    recordsFiltered: int
    recordsTotal: int
    draw: Optional[int]


class TracksResponse(DataTableResponse[Track]):
    pass


class ArtistsResponse(DataTableResponse[Artist]):
    pass


class AlbumsResponse(DataTableResponse[Album]):
    pass
