-- This table should only have a single row
CREATE TABLE fb_group (
  id PRIMARY KEY NOT NULL,
  owner_name TEXT,
  group_id TEXT,
  name TEXT,
  description TEXT,
  updated_time DATETIME
);

-- This is the only row in the group table
INSERT INTO fb_group VALUES (1, NULL, NULL, NULL, NULL, NULL);
