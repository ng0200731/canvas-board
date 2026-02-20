-- ============================================================
-- Canva Board Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    display_name  TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    is_active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS boards (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT DEFAULT '',
    owner_id      TEXT NOT NULL REFERENCES users(id),
    view_mode     TEXT NOT NULL DEFAULT 'flowchart',
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS board_members (
    board_id   TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT 'editor',
    added_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (board_id, user_id)
);

CREATE TABLE IF NOT EXISTS cards (
    id            TEXT PRIMARY KEY,
    board_id      TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    title         TEXT NOT NULL DEFAULT 'Untitled',
    body          TEXT DEFAULT '',
    pos_x         REAL NOT NULL DEFAULT 0,
    pos_y         REAL NOT NULL DEFAULT 0,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS card_files (
    id            TEXT PRIMARY KEY,
    card_id       TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name   TEXT NOT NULL,
    mime_type     TEXT NOT NULL,
    file_size     INTEGER NOT NULL,
    uploaded_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tags (
    id    TEXT PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS card_tags (
    card_id TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    tag_id  TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (card_id, tag_id)
);

CREATE TABLE IF NOT EXISTS connections (
    id            TEXT PRIMARY KEY,
    board_id      TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    from_card_id  TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    to_card_id    TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    label         TEXT DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shares (
    id            TEXT PRIMARY KEY,
    board_id      TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    created_by    TEXT NOT NULL REFERENCES users(id),
    expires_at    TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS emails (
    id            TEXT PRIMARY KEY,
    imap_uid      TEXT UNIQUE NOT NULL,
    from_addr     TEXT NOT NULL,
    subject       TEXT NOT NULL,
    body_text     TEXT DEFAULT '',
    body_html     TEXT DEFAULT '',
    received_at   TEXT NOT NULL,
    processed     INTEGER NOT NULL DEFAULT 0,
    board_id      TEXT REFERENCES boards(id),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_attachments (
    id            TEXT PRIMARY KEY,
    email_id      TEXT NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name   TEXT NOT NULL,
    mime_type     TEXT NOT NULL,
    file_size     INTEGER NOT NULL,
    uploaded_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_cards_board ON cards(board_id);
CREATE INDEX IF NOT EXISTS idx_card_files_card ON card_files(card_id);
CREATE INDEX IF NOT EXISTS idx_card_tags_card ON card_tags(card_id);
CREATE INDEX IF NOT EXISTS idx_card_tags_tag ON card_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_connections_board ON connections(board_id);
CREATE INDEX IF NOT EXISTS idx_shares_board ON shares(board_id);
CREATE INDEX IF NOT EXISTS idx_emails_processed ON emails(processed);
CREATE INDEX IF NOT EXISTS idx_board_members_user ON board_members(user_id);
