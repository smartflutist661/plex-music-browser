INSERT INTO metadata_items (id, title, parent_id, metadata_type, title_sort)
VALUES 
(1, 'Artist 1',null, 8, 'arb'),
(2, 'Artist 2',null, 8, 'arb'),
(3, 'Artist 3',null, 8, 'arb'),
(4, 'Album 1', 1,9, 'arb'),
(5, 'Album 2',1,9, 'arb'),
(6, 'Album 3',2,9, 'arb'),
(7,   'Track 1',4, 10, 'arb'),
(8,    'Track 2',4, 10, 'arb'),
(9,    'Track 1', 5, 10, 'arb'),
(10,   'Track 2',5, 10, 'arb'),
(11,   'Track 3',5, 10, 'arb'),
(12,   'Track 1',6, 10, 'arb'),
(13,   'Track 2', 6,10, 'arb'),
(14,   'Track 3', 6,10, 'arb'),
(15,  'Track 4',6, 10, 'arb');
