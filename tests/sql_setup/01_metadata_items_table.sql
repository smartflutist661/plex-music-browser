CREATE TABLE metadata_items (
	id int primary key,
	parent_id int,
	guid text,
	title text,
	title_sort text,
	metadata_type int
);
