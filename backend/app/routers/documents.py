import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_unlocked_vault
from app.models.job import Job
from app.models.capture import Capture
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.document_service import store_document, get_document_full_path
from app.utils.hashing import sha256_file

router = APIRouter(
    prefix="/jobs/{job_id}/documents",
    tags=["documents"],
    dependencies=[Depends(require_unlocked_vault)],
)


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        job_id=doc.job_id,
        doc_type=doc.doc_type,
        original_filename=doc.original_filename,
        stored_path=doc.stored_path,
        file_hash=doc.file_hash,
        file_size_bytes=doc.file_size_bytes,
        version_label=doc.version_label,
        mime_type=doc.mime_type,
        created_at=doc.created_at,
        submitted_at=doc.submitted_at,
    )


VALID_DOC_TYPES = {"cv", "cover_letter", "research_statement",
                   "teaching_statement", "transcript", "portfolio", "other"}


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    job_id: str,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    version_label: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type. Must be one of: {VALID_DOC_TYPES}")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Security: enforce upload size limit to prevent memory/disk DoS.
    # Improvement: rejects oversized files early.
    max_bytes = settings.max_upload_bytes
    size = 0
    chunks: list[bytes] = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=413, detail=f"File too large (max {max_bytes} bytes)")
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    stored_path, file_hash, file_size = store_document(job_id, file.filename, content)

    # Check for duplicate
    existing = db.query(Document).filter(
        Document.job_id == job_id,
        Document.file_hash == file_hash,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Document with identical content already exists for this job")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = Document(
        id=str(uuid.uuid4()),
        job_id=job_id,
        doc_type=doc_type,
        original_filename=file.filename,
        stored_path=stored_path,
        file_hash=file_hash,
        file_size_bytes=file_size,
        version_label=version_label,
        mime_type=file.content_type,
        created_at=now,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_to_response(doc)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    docs = db.query(Document).filter(Document.job_id == job_id).order_by(Document.created_at.desc()).all()
    return [_doc_to_response(d) for d in docs]


@router.put("/{doc_id}/submit", response_model=DocumentResponse)
async def mark_submitted(job_id: str, doc_id: str, db: Session = Depends(get_db)):
    """Mark a document as submitted for this job application."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.submitted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.commit()
    db.refresh(doc)
    return _doc_to_response(doc)


@router.delete("/{doc_id}/submit", response_model=DocumentResponse)
async def unmark_submitted(job_id: str, doc_id: str, db: Session = Depends(get_db)):
    """Remove the submitted mark from a document."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.submitted_at = None
    db.commit()
    db.refresh(doc)
    return _doc_to_response(doc)


@router.get("/{doc_id}/verify")
async def verify_document(job_id: str, doc_id: str, db: Session = Depends(get_db)):
    """Re-hash the stored file and compare against the recorded SHA-256."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    full_path = get_document_full_path(doc.stored_path, settings.vault_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing from vault")

    actual_hash = sha256_file(full_path)
    verified = actual_hash == doc.file_hash

    return {
        "verified": verified,
        "filename": doc.original_filename,
        "stored_hash": doc.file_hash,
        "actual_hash": actual_hash,
    }


@router.get("/{doc_id}/match")
async def match_document(job_id: str, doc_id: str, db: Session = Depends(get_db)):
    """Keyword overlap score between this document and the job's captured text."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    full_path = get_document_full_path(doc.stored_path, settings.vault_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing from vault")

    # Combine all capture text snapshots for this job
    captures = db.query(Capture).filter(Capture.job_id == job_id).all()
    job_text = " ".join(c.text_snapshot for c in captures if c.text_snapshot)

    from app.services.match_service import extract_text_from_file, compute_match
    doc_text = extract_text_from_file(full_path, doc.mime_type)

    return compute_match(job_text, doc_text)


@router.get("/{doc_id}/download")
async def download_document(job_id: str, doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.job_id == job_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    full_path = get_document_full_path(doc.stored_path, settings.vault_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing from vault")

    return FileResponse(
        path=str(full_path),
        filename=doc.original_filename,
        media_type=doc.mime_type or "application/octet-stream",
    )
