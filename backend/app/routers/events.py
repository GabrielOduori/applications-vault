import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_unlocked_vault
from app.models.job import Job
from app.models.event import Event
from app.schemas.event import EventCreate, EventResponse

router = APIRouter(tags=["events"], dependencies=[Depends(require_unlocked_vault)])

VALID_EVENTS = {"SAVED", "SHORTLISTED", "DRAFTING", "SUBMITTED",
                "INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN", "EXPIRED"}


def _event_to_response(ev: Event) -> EventResponse:
    return EventResponse(
        id=ev.id,
        job_id=ev.job_id,
        event_type=ev.event_type,
        notes=ev.notes,
        next_action_date=ev.next_action_date,
        occurred_at=ev.occurred_at,
    )


@router.post("/jobs/{job_id}/events", response_model=EventResponse, status_code=201)
async def add_event(job_id: str, req: EventCreate, db: Session = Depends(get_db)):
    if req.event_type not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of: {VALID_EVENTS}")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event = Event(
        id=str(uuid.uuid4()),
        job_id=job_id,
        event_type=req.event_type,
        notes=req.notes,
        next_action_date=req.next_action_date,
        occurred_at=now,
    )
    db.add(event)

    # Auto follow-up reminders when a job is marked SUBMITTED
    if req.event_type == "SUBMITTED":
        today = date.today()
        for days, label in [(7, "7 days"), (14, "14 days")]:
            reminder_date = (today + timedelta(days=days)).isoformat()
            reminder = Event(
                id=str(uuid.uuid4()),
                job_id=job_id,
                event_type="SUBMITTED",
                notes=f"Follow-up reminder — check for response after {label}",
                next_action_date=reminder_date,
                occurred_at=now,
            )
            db.add(reminder)

    # Update job status
    job.status = req.event_type
    job.updated_at = now
    db.commit()
    db.refresh(event)
    return _event_to_response(event)


@router.get("/jobs/{job_id}/events", response_model=list[EventResponse])
async def list_events(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    events = db.query(Event).filter(Event.job_id == job_id).order_by(Event.occurred_at.asc()).all()
    return [_event_to_response(e) for e in events]


@router.get("/events/upcoming", response_model=list[EventResponse])
async def upcoming_events(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = (
        db.query(Event)
        .filter(Event.next_action_date.isnot(None))
        .filter(Event.next_action_date >= now[:10])  # Compare date portion
        .order_by(Event.next_action_date.asc())
        .all()
    )
    return [_event_to_response(e) for e in events]
