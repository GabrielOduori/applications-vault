import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_unlocked_vault
from app.models.job import Job
from app.models.tag import Tag, job_tags
from app.schemas.tag import TagCreate, TagUpdate, TagResponse

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    dependencies=[Depends(require_unlocked_vault)],
)


def _tag_to_response(tag: Tag, db: Session) -> TagResponse:
    count = db.query(func.count(job_tags.c.job_id)).filter(job_tags.c.tag_id == tag.id).scalar()
    return TagResponse(id=tag.id, name=tag.name, color=tag.color, job_count=count)


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(req: TagCreate, db: Session = Depends(get_db)):
    existing = db.query(Tag).filter(Tag.name == req.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")

    tag = Tag(id=str(uuid.uuid4()), name=req.name, color=req.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _tag_to_response(tag, db)


@router.get("", response_model=list[TagResponse])
async def list_tags(db: Session = Depends(get_db)):
    tags = db.query(Tag).order_by(Tag.name).all()
    return [_tag_to_response(t, db) for t in tags]


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: str, req: TagUpdate, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if req.name is not None:
        tag.name = req.name
    if req.color is not None:
        tag.color = req.color
    db.commit()
    db.refresh(tag)
    return _tag_to_response(tag, db)


@router.delete("/{tag_id}")
async def delete_tag(tag_id: str, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()
    return {"message": "Tag deleted"}


# Job-tag association endpoints
tag_jobs_router = APIRouter(
    prefix="/jobs/{job_id}/tags",
    tags=["tags"],
    dependencies=[Depends(require_unlocked_vault)],
)


@tag_jobs_router.post("", status_code=201)
async def add_tag_to_job(job_id: str, req: TagCreate, db: Session = Depends(get_db)):
    """Associate an existing tag with a job. req.name is used to find the tag."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tag = db.query(Tag).filter(Tag.name == req.name).first()
    if not tag:
        # Create tag if it doesn't exist
        tag = Tag(id=str(uuid.uuid4()), name=req.name, color=req.color)
        db.add(tag)

    if tag not in job.tags:
        job.tags.append(tag)
    db.commit()
    return {"message": f"Tag '{req.name}' added to job"}


@tag_jobs_router.delete("/{tag_id}")
async def remove_tag_from_job(job_id: str, tag_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    if tag in job.tags:
        job.tags.remove(tag)
    db.commit()
    return {"message": "Tag removed from job"}
