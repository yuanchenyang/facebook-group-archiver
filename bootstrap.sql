CREATE TABLE post (
  id TEXT PRIMARY KEY UNIQUE,
  created_time DATETIME NOT NULL,
  updated_time DATETIME NOT NULL,
  from_name TEXT NOT NULL,
  from_id TEXT DEFAULT NULL,
  to_name TEXT DEFAULT NULL,
  message TEXT DEFAULT NULL,
  link TEXT DEFAULT NULL,
  name TEXT DEFAULT NULL,
  caption TEXT DEFAULT NULL,
  description TEXT DEFAULT NULL,
  source TEXT DEFAULT NULL,
  type TEXT DEFAULT NULL,
  place TEXT DEFAULT NULL
);

CREATE TABLE comment (
  id TEXT PRIMARY KEY UNIQUE,
  post_id TEXT NOT NULL,
  from_name TEXT NOT NULL,
  message TEXT NOT NULL,
  created_time DATETIME NOT NULL,
  FOREIGN KEY(post_id) REFERENCES post(id)
);

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

CREATE VIRTUAL TABLE post_fts USING fts3(
  post_id TEXT UNIQUE NOT NULL REFERENCES post(id),
  body TEXT DEFAULT NULL
);

CREATE VIRTUAL TABLE comment_fts USING fts3(
  comment_id TEXT UNIQUE NOT NULL REFERENCES comment(id),
  body TEXT DEFAULT NULL
);
