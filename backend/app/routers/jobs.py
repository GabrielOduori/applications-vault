import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_unlocked_vault
from app.models.job import Job
from app.models.capture import Capture
from app.models.event import Event
from app.models.document import Document
from app.models.tag import Tag
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobListResponse
from app.utils.filesystem import ensure_job_dirs

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(require_unlocked_vault)],
)


def _job_to_response(job: Job, db: Session) -> JobResponse:
    capture_count = db.query(func.count(Capture.id)).filter(Capture.job_id == job.id).scalar()
    event_count = db.query(func.count(Event.id)).filter(Event.job_id == job.id).scalar()
    document_count = db.query(func.count(Document.id)).filter(Document.job_id == job.id).scalar()
    tag_names = [t.name for t in job.tags]

    return JobResponse(
        id=job.id,
        title=job.title,
        organisation=job.organisation,
        url=job.url,
        location=job.location,
        salary_range=job.salary_range,
        deadline_type=job.deadline_type,
        deadline_date=job.deadline_date,
        status=job.status,
        notes=job.notes,
        created_at=job.created_at,
        updated_at=job.updated_at,
        capture_count=capture_count,
        event_count=event_count,
        document_count=document_count,
        tags=tag_names,
    )


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(req: JobCreate, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    job_id = str(uuid.uuid4())

    job = Job(
        id=job_id,
        title=req.title,
        organisation=req.organisation,
        url=req.url,
        location=req.location,
        salary_range=req.salary_range,
        deadline_type=req.deadline_type,
        deadline_date=req.deadline_date,
        status="SAVED",
        notes=req.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(job)

    # Auto-create SAVED event
    event = Event(
        id=str(uuid.uuid4()),
        job_id=job_id,
        event_type="SAVED",
        notes="Job saved",
        occurred_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(job)

    ensure_job_dirs(job_id)
    return _job_to_response(job, db)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Job)

    if status:
        query = query.filter(Job.status == status)
    if tag:
        query = query.join(Job.tags).filter(Tag.name == tag)
    if q:
        query = query.filter(
            Job.title.ilike(f"%{q}%")
            | Job.organisation.ilike(f"%{q}%")
            | Job.notes.ilike(f"%{q}%")
        )

    total = query.count()
    jobs = query.order_by(Job.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return JobListResponse(
        jobs=[_job_to_response(j, db) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job, db)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, req: JobUpdate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    job.updated_at = now

    db.commit()
    db.refresh(job)
    return _job_to_response(job, db)


@router.delete("/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"message": "Job deleted"}
