from pathlib import Path
from app.config import settings


def ensure_vault_dirs(vault_path: Path | None = None) -> Path:
    path = vault_path or settings.vault_path
    path.mkdir(parents=True, exist_ok=True)
    (path / "jobs").mkdir(exist_ok=True)
    return path


def ensure_job_dirs(job_id: str, vault_path: Path | None = None) -> Path:
    path = vault_path or settings.vault_path
    job_dir = path / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "captures").mkdir(exist_ok=True)
    (job_dir / "documents").mkdir(exist_ok=True)
    return job_dir


def sanitize_filename(name: str) -> str:
    keep = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    return "".join(c if c in keep else "_" for c in name)
