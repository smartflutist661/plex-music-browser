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
artists AS (
    SELECT
        artist.id as id,
        artist.title as artist,
        artist.title as artist_sort,
        mis.rating as rating,
        mis.last_rated_at as last_rated_at,
        genres.genres as genres,
        styles.styles as styles
    FROM metadata_items artist
    left join metadata_item_settings mis on artist.guid = mis.guid
    left join genres on genres.metadata_item_id = artist.id
    left join styles on styles.metadata_item_id = artist.id
    where artist.metadata_type = 8
)