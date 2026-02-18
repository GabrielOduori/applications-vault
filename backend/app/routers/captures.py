import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_unlocked_vault
from app.models.job import Job
from app.models.capture import Capture
from app.models.event import Event
from app.models.document import Document
from app.schemas.capture import CaptureCreate, CaptureResponse, QuickCaptureRequest, QuickCaptureResponse
from app.schemas.job import JobResponse
from app.services.capture_service import store_html_snapshot
from app.services.document_service import store_document
from app.services.pdf_service import generate_capture_pdf
from app.utils.filesystem import ensure_job_dirs

router = APIRouter(tags=["captures"], dependencies=[Depends(require_unlocked_vault)])


def _capture_to_response(cap: Capture) -> CaptureResponse:
    return CaptureResponse(
        id=cap.id,
        job_id=cap.job_id,
        url=cap.url,
        page_title=cap.page_title,
        text_snapshot=cap.text_snapshot,
        html_path=cap.html_path,
        pdf_path=cap.pdf_path,
        capture_method=cap.capture_method,
        captured_at=cap.captured_at,
    )


@router.post("/jobs/{job_id}/captures", response_model=CaptureResponse, status_code=201)
async def create_capture(job_id: str, req: CaptureCreate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Security: cap capture payload sizes to prevent oversized content DoS.
    # Improvement: limits memory/disk impact from large snapshots.
    if req.text_snapshot and len(req.text_snapshot) > settings.max_text_snapshot_chars:
        raise HTTPException(status_code=413, detail="text_snapshot too large")
    if req.html_content and len(req.html_content) > settings.max_html_content_chars:
        raise HTTPException(status_code=413, detail="html_content too large")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    capture_id = str(uuid.uuid4())

    html_path = None
    if req.html_content:
        html_path = store_html_snapshot(job_id, capture_id, req.html_content)

    capture = Capture(
        id=capture_id,
        job_id=job_id,
        url=req.url,
        page_title=req.page_title,
        text_snapshot=req.text_snapshot,
        html_path=html_path,
        capture_method=req.capture_method,
        captured_at=now,
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)
    return _capture_to_response(capture)


@router.get("/jobs/{job_id}/captures", response_model=list[CaptureResponse])
async def list_captures(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    captures = db.query(Capture).filter(Capture.job_id == job_id).order_by(Capture.captured_at.desc()).all()
    return [_capture_to_response(c) for c in captures]


@router.post("/captures/quick", response_model=QuickCaptureResponse, status_code=201)
async def quick_capture(req: QuickCaptureRequest, db: Session = Depends(get_db)):
    # Duplicate check — same URL already in vault
    if req.url:
        existing = db.query(Job).filter(Job.url == req.url).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f'Already captured: "{existing.title}" (id={existing.id})',
            )

    # Security: cap capture payload sizes to prevent oversized content DoS.
    # Improvement: limits memory/disk impact from large snapshots.
    if req.text_snapshot and len(req.text_snapshot) > settings.max_text_snapshot_chars:
        raise HTTPException(status_code=413, detail="text_snapshot too large")
    if req.html_content and len(req.html_content) > settings.max_html_content_chars:
        raise HTTPException(status_code=413, detail="html_content too large")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    job_id = str(uuid.uuid4())
    capture_id = str(uuid.uuid4())

    title = req.title or req.page_title or "Untitled Job"
    # Normalise deadline to YYYY-MM-DD if possible
    deadline_date = _parse_deadline(req.deadline) if req.deadline else None

    job = Job(
        id=job_id,
        title=title,
        organisation=req.organisation,
        url=req.url,
        location=req.location,
        deadline_date=deadline_date,
        deadline_type="fixed" if deadline_date else "unknown",
        status="SAVED",
        created_at=now,
        updated_at=now,
    )
    db.add(job)

    saved_event = Event(
        id=str(uuid.uuid4()),
        job_id=job_id,
        event_type="SAVED",
        notes="Quick capture from browser" + (f" — deadline: {req.deadline}" if req.deadline else ""),
        next_action_date=deadline_date,
        occurred_at=now,
    )
    db.add(saved_event)

    ensure_job_dirs(job_id)

    html_path = None
    if req.html_content:
        html_path = store_html_snapshot(job_id, capture_id, req.html_content)

    # Generate PDF archive of the posting
    pdf_bytes = generate_capture_pdf(
        title=title,
        organisation=req.organisation,
        url=req.url,
        text_snapshot=req.text_snapshot,
        captured_at=now,
        deadline=req.deadline,
    )
    safe_title = "".join(c for c in title[:40] if c.isalnum() or c in " -_").strip().replace(" ", "_")
    pdf_filename = f"capture_{safe_title}.pdf"
    pdf_rel_path, pdf_hash, pdf_size = store_document(job_id, pdf_filename, pdf_bytes)

    # Store PDF as an immutable document record
    doc = Document(
        id=str(uuid.uuid4()),
        job_id=job_id,
        original_filename=pdf_filename,
        doc_type="job_posting",
        stored_path=pdf_rel_path,
        file_hash=pdf_hash,
        file_size_bytes=pdf_size,
        mime_type="application/pdf",
        created_at=now,
    )
    db.add(doc)

    capture = Capture(
        id=capture_id,
        job_id=job_id,
        url=req.url,
        page_title=req.page_title,
        text_snapshot=req.text_snapshot,
        html_path=html_path,
        pdf_path=pdf_rel_path,
        capture_method=req.capture_method,
        captured_at=now,
    )
    db.add(capture)
    db.commit()
    db.refresh(job)
    db.refresh(capture)

    from app.routers.jobs import _job_to_response
    return QuickCaptureResponse(
        job=_job_to_response(job, db),
        capture=_capture_to_response(capture),
    )


def _parse_deadline(raw: str) -> str | None:
    """Try to parse a deadline string into YYYY-MM-DD. Returns None if unparseable."""
    import re

    raw = raw.strip()

    # Already ISO format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
        return raw

    formats = [
        '%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y',
        '%d %B %Y', '%d %b %Y',
        '%m/%d/%Y', '%d/%m/%Y',
    ]

    # Strip ordinal suffixes: 15th -> 15
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', raw, flags=re.IGNORECASE)

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None
