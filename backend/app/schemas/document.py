from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    job_id: str
    doc_type: str
    original_filename: str
    stored_path: str
    file_hash: str
    file_size_bytes: int
    version_label: str | None
    mime_type: str | None
    created_at: str
    submitted_at: str | None
