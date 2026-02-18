from pathlib import Path
from app.config import settings
from app.utils.filesystem import ensure_job_dirs


def store_html_snapshot(job_id: str, capture_id: str, html_content: str) -> str:
    job_dir = ensure_job_dirs(job_id)
    filename = f"{capture_id}.html"
    filepath = job_dir / "captures" / filename
    filepath.write_text(html_content, encoding="utf-8")
    return f"jobs/{job_id}/captures/{filename}"
