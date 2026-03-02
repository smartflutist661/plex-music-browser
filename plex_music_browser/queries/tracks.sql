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
tracks AS (
    SELECT
    	track.id as id,
        track.title as track,
        track.title_sort as track_sort,
        mis.rating as rating,
        mis.last_rated_at as last_rated_at,
        album.id as album_id,
        album.title as album,
        album.title_sort as album_sort,
        artist.id as artist_id,
        artist.title as artist,
        artist.title_sort as artist_sort,
        genres.genres as genres,
        styles.styles as styles
    FROM metadata_items track
    join metadata_items album on track.parent_id = album.id
    join metadata_items artist on album.parent_id = artist.id
    left join metadata_item_settings mis on track.guid = mis.guid
    left join genres on genres.metadata_item_id = track.id
    left join styles on styles.metadata_item_id = track.id
    where track.metadata_type = 10
)