
CREATE TABLE post (
  id TEXT PRIMARY KEY UNIQUE,
  created_time DATETIME NOT NULL,
  updated_time DATETIME NOT NULL,
  from_name TEXT NOT NULL,
  search_string NOT NULL,
  to_name TEXT DEFAULT NULL,
  message TEXT DEFAULT NULL,
  link TEXT DEFAULT NULL,
  name TEXT DEFAULT NULL,
  caption TEXT DEFAULT NULL,
  description TEXT DEFAULT NULL,
  source TEXT DEFAULT NULL,
  type TEXT DEFAULT NULL
);

CREATE TABLE comment (
  id TEXT PRIMARY KEY UNIQUE,
  post_id TEXT REFERENCES post(id) NOT NULL,
  from_name TEXT NOT NULL,
  message TEXT NOT NULL,
  created_time DATETIME NOT NULL
);
