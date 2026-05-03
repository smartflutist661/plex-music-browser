with genres as (
    select
        taggings.metadata_item_id,
        string_agg(tags.tag, '|') as genres
    from taggings
    join tags on taggings.tag_id = tags.id
    where tags.tag_type = 1
    group by taggings.metadata_item_id
),
styles as (
    select
        taggings.metadata_item_id,
        string_agg(tags.tag, '|') as styles
    from taggings
    join tags on taggings.tag_id = tags.id
    where tags.tag_type = 301
    group by taggings.metadata_item_id
),
albums AS (
    SELECT
        album.id as id,
        album.title as album,
        album.title_sort as album_sort,
        mis.rating as rating,
        mis.last_rated_at as last_rated_at,
        artist.id as artist_id,
        artist.title as artist,
        artist.title_sort as artist_sort,
        genres.genres as genres,
        styles.styles as styles,
        sum(track_media.duration) as 'length',
        avg(track_mis.rating) as avg_track_rating
    from metadata_items album
    join metadata_items artist on album.parent_id = artist.id
    join metadata_items track on track.parent_id = album.id
    join media_items track_media on track.id = track_media.metadata_item_id
    left join metadata_item_settings mis on album.guid = mis.guid
    left join metadata_item_settings track_mis on track.guid = track_mis.guid
    left join genres on genres.metadata_item_id = album.id
    left join styles on styles.metadata_item_id = album.id
    where album.metadata_type = 9
    group by album.id
)