-- Migration number: 0001 	 initial schema

CREATE TABLE users (
  username TEXT PRIMARY KEY,
  conversation_id TEXT,
  telegram_user_id INTEGER UNIQUE
);

CREATE TABLE entries (
  id TEXT PRIMARY KEY,              -- uuid4 string, legacy ids preserved
  created_at TEXT NOT NULL,         -- 'YYYY-MM-DD HH:MM:SS' (legacy format kept; new rows use same format, UTC)
  conversation_id TEXT,             -- telegram chat id where created (kept for parity)
  sender TEXT NOT NULL,             -- username, no leading @
  recipient TEXT NOT NULL,
  amount REAL NOT NULL,             -- legacy stored strings; cast to REAL
  description TEXT,
  deleted INTEGER NOT NULL DEFAULT 0,
  deleted_at TEXT
);
CREATE INDEX idx_entries_sender ON entries(sender);
CREATE INDEX idx_entries_recipient ON entries(recipient);

CREATE TABLE sessions (             -- grammY session/conversation storage adapter
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
