import os
from pathlib import Path

from app.utils.filesystem import ensure_job_dirs, sanitize_filename
from app.utils.hashing import sha256_bytes


def store_document(job_id: str, filename: str, content: bytes) -> tuple[str, str, int]:
    """Store a document immutably. Returns (relative_path, file_hash, file_size)."""
    file_hash = sha256_bytes(content)
    safe_name = sanitize_filename(filename)
    stored_name = f"{file_hash[:8]}_{safe_name}"

    job_dir = ensure_job_dirs(job_id)
    doc_path = job_dir / "documents" / stored_name
    doc_path.write_bytes(content)
    os.chmod(doc_path, 0o444)

    relative_path = f"jobs/{job_id}/documents/{stored_name}"
    return relative_path, file_hash, len(content)


def get_document_full_path(stored_path: str, vault_path: Path) -> Path:
    return vault_path / stored_path
