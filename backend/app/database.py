import sqlite3
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _set_sqlite_pragmas(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine(db_path: Path | None = None):
    path = db_path or settings.db_path
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SCHEMA_SQL = """\
-- ============================================================
-- VAULT CONFIGURATION
-- ============================================================
CREATE TABLE IF NOT EXISTS vault_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- ============================================================
-- AUTH THROTTLE
-- ============================================================
CREATE TABLE IF NOT EXISTS auth_throttle (
    key             TEXT PRIMARY KEY,
    failed_attempts INTEGER NOT NULL,
    last_failed_at  REAL NOT NULL
);

-- ============================================================
-- JOBS
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    organisation  TEXT,
    url           TEXT,
    location      TEXT,
    salary_range  TEXT,
    deadline_type TEXT CHECK(deadline_type IN ('fixed','rolling','unknown')) DEFAULT 'unknown',
    deadline_date TEXT,
    status        TEXT NOT NULL DEFAULT 'SAVED'
                  CHECK(status IN ('SAVED','SHORTLISTED','DRAFTING','SUBMITTED',
                                   'INTERVIEW','OFFER','REJECTED','WITHDRAWN','EXPIRED')),
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs(deadline_date);
CREATE INDEX IF NOT EXISTS idx_jobs_organisation ON jobs(organisation);

-- ============================================================
-- CAPTURES
-- ============================================================
CREATE TABLE IF NOT EXISTS captures (
    id             TEXT PRIMARY KEY,
    job_id         TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    url            TEXT,
    page_title     TEXT,
    text_snapshot  TEXT,
    html_path      TEXT,
    pdf_path       TEXT,
    capture_method TEXT NOT NULL
                   CHECK(capture_method IN ('structured','generic_html','dom_render',
                                            'text_selection','pdf_snapshot','manual_paste')),
    captured_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_captures_job ON captures(job_id);

-- ============================================================
-- EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    id               TEXT PRIMARY KEY,
    job_id           TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    event_type       TEXT NOT NULL
                     CHECK(event_type IN ('SAVED','SHORTLISTED','DRAFTING','SUBMITTED',
                                          'INTERVIEW','OFFER','REJECTED','WITHDRAWN','EXPIRED')),
    notes            TEXT,
    next_action_date TEXT,
    occurred_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_next_action ON events(next_action_date);

-- ============================================================
-- DOCUMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id                TEXT PRIMARY KEY,
    job_id            TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    doc_type          TEXT NOT NULL
                      CHECK(doc_type IN ('cv','cover_letter','research_statement',
                                         'teaching_statement','transcript','portfolio',
                                         'job_posting','other')),
    original_filename TEXT NOT NULL,
    stored_path       TEXT NOT NULL,
    file_hash         TEXT NOT NULL,
    file_size_bytes   INTEGER NOT NULL,
    version_label     TEXT,
    mime_type         TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    submitted_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_job ON documents(job_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_path ON documents(stored_path);

-- ============================================================
-- TAGS
-- ============================================================
CREATE TABLE IF NOT EXISTS tags (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE,
    color TEXT
);

CREATE TABLE IF NOT EXISTS job_tags (
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, tag_id)
);

-- ============================================================
-- FTS5
-- ============================================================
CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
    title, organisation, location, notes,
    content='jobs', content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS captures_fts USING fts5(
    page_title, text_snapshot,
    content='captures', content_rowid='rowid'
);
"""

FTS_TRIGGERS_SQL = """\
-- Jobs FTS sync triggers
CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
    INSERT INTO jobs_fts(rowid, title, organisation, location, notes)
    VALUES (new.rowid, new.title, new.organisation, new.location, new.notes);
END;

CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, organisation, location, notes)
    VALUES ('delete', old.rowid, old.title, old.organisation, old.location, old.notes);
END;

CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, organisation, location, notes)
    VALUES ('delete', old.rowid, old.title, old.organisation, old.location, old.notes);
    INSERT INTO jobs_fts(rowid, title, organisation, location, notes)
    VALUES (new.rowid, new.title, new.organisation, new.location, new.notes);
END;

-- Captures FTS sync triggers
CREATE TRIGGER IF NOT EXISTS captures_ai AFTER INSERT ON captures BEGIN
    INSERT INTO captures_fts(rowid, page_title, text_snapshot)
    VALUES (new.rowid, new.page_title, new.text_snapshot);
END;

CREATE TRIGGER IF NOT EXISTS captures_ad AFTER DELETE ON captures BEGIN
    INSERT INTO captures_fts(captures_fts, rowid, page_title, text_snapshot)
    VALUES ('delete', old.rowid, old.page_title, old.text_snapshot);
END;

CREATE TRIGGER IF NOT EXISTS captures_au AFTER UPDATE ON captures BEGIN
    INSERT INTO captures_fts(captures_fts, rowid, page_title, text_snapshot)
    VALUES ('delete', old.rowid, old.page_title, old.text_snapshot);
    INSERT INTO captures_fts(rowid, page_title, text_snapshot)
    VALUES (new.rowid, new.page_title, new.text_snapshot);
END;
"""


MIGRATIONS = [
    # v0.2: submitted document linking
    "ALTER TABLE documents ADD COLUMN submitted_at TEXT",
    # v0.3: auth throttle table
    "CREATE TABLE IF NOT EXISTS auth_throttle (key TEXT PRIMARY KEY, failed_attempts INTEGER NOT NULL, last_failed_at REAL NOT NULL)",
]


def init_db(db_path: Path | None = None):
    path = db_path or settings.db_path
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA_SQL)
    conn.executescript(FTS_TRIGGERS_SQL)
    # Run migrations idempotently (ALTER TABLE fails silently if column exists)
    for migration in MIGRATIONS:
        try:
            conn.execute(migration)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.close()
