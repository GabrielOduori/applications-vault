import sqlite3
from app.config import settings


def search_fts(query: str, scope: str = "all", limit: int = 20, offset: int = 0) -> list[dict]:
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    results = []

    if scope in ("all", "jobs"):
        try:
            cursor = conn.execute(
                """
                SELECT j.id as job_id, j.title as job_title, j.organisation,
                       'job' as source,
                       snippet(jobs_fts, 0, '<mark>', '</mark>', '...', 32) as snippet,
                       rank
                FROM jobs_fts
                JOIN jobs j ON j.rowid = jobs_fts.rowid
                WHERE jobs_fts MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
                """,
                (query, limit, offset),
            )
        except sqlite3.OperationalError as exc:
            # Security: surface invalid FTS queries as 400 instead of 500.
            # Improvement: prevents malformed search input from crashing the API.
            conn.close()
            raise ValueError("Invalid search query") from exc
        results.extend([dict(r) for r in cursor.fetchall()])

    if scope in ("all", "captures"):
        try:
            cursor = conn.execute(
                """
                SELECT j.id as job_id, j.title as job_title, j.organisation,
                       'capture' as source,
                       snippet(captures_fts, 1, '<mark>', '</mark>', '...', 64) as snippet,
                       rank
                FROM captures_fts
                JOIN captures c ON c.rowid = captures_fts.rowid
                JOIN jobs j ON j.id = c.job_id
                WHERE captures_fts MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
                """,
                (query, limit, offset),
            )
        except sqlite3.OperationalError as exc:
            # Security: surface invalid FTS queries as 400 instead of 500.
            # Improvement: prevents malformed search input from crashing the API.
            conn.close()
            raise ValueError("Invalid search query") from exc
        results.extend([dict(r) for r in cursor.fetchall()])

    conn.close()
    results.sort(key=lambda r: r["rank"])
    return results
