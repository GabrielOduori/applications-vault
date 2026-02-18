import csv
import io
import json
import sqlite3
import zipfile
from pathlib import Path

from app.config import settings


def export_vault_zip() -> io.BytesIO:
    buf = io.BytesIO()
    vault_path = settings.vault_path
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in vault_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(vault_path)
                zf.write(file_path, arcname)
    buf.seek(0)
    return buf


def export_csv() -> str:
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row

    output = io.StringIO()
    writer = csv.writer(output)

    # Jobs with latest event
    writer.writerow([
        "job_id", "title", "organisation", "url", "location", "salary_range",
        "deadline_type", "deadline_date", "status", "notes", "created_at", "updated_at",
    ])
    for row in conn.execute("SELECT * FROM jobs ORDER BY created_at DESC"):
        writer.writerow([
            row["id"], row["title"], row["organisation"], row["url"],
            row["location"], row["salary_range"], row["deadline_type"],
            row["deadline_date"], row["status"], row["notes"],
            row["created_at"], row["updated_at"],
        ])

    conn.close()
    return output.getvalue()


def export_json() -> dict:
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row

    data = {"version": "1", "jobs": [], "tags": []}

    for job_row in conn.execute("SELECT * FROM jobs ORDER BY created_at DESC"):
        job = dict(job_row)
        job["captures"] = [dict(r) for r in conn.execute(
            "SELECT * FROM captures WHERE job_id = ? ORDER BY captured_at", (job["id"],)
        )]
        job["events"] = [dict(r) for r in conn.execute(
            "SELECT * FROM events WHERE job_id = ? ORDER BY occurred_at", (job["id"],)
        )]
        job["documents"] = [dict(r) for r in conn.execute(
            "SELECT * FROM documents WHERE job_id = ? ORDER BY created_at", (job["id"],)
        )]
        job["tags"] = [dict(r) for r in conn.execute(
            "SELECT t.* FROM tags t JOIN job_tags jt ON t.id = jt.tag_id WHERE jt.job_id = ?", (job["id"],)
        )]
        data["jobs"].append(job)

    data["tags"] = [dict(r) for r in conn.execute("SELECT * FROM tags ORDER BY name")]
    conn.close()
    return data
