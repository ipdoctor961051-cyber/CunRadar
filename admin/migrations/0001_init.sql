CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO settings (key, value) VALUES (
  'follow_config',
  '{"youtube":[],"bilibili":[],"rss":[],"github":[],"github_trending":{"enabled":true,"language":"","limit":5}}'
);
