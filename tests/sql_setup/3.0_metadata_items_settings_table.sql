-- Maybe this will get tests someday; for now, table just needs to exist
CREATE TABLE metadata_item_settings (
	guid text,
	rating float,
	last_rated_at dt_integer(8)
);
