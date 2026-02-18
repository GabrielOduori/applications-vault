from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_unlocked_vault
from app.models.job import Job
from app.services.calendar_service import generate_job_ics

router = APIRouter(tags=["calendar"], dependencies=[Depends(require_unlocked_vault)])


@router.get("/jobs/{job_id}/calendar")
async def job_calendar(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.deadline_date:
        raise HTTPException(status_code=400, detail="Job has no deadline set")

    ics_data = generate_job_ics(
        title=job.title,
        organisation=job.organisation,
        url=job.url,
        notes=job.notes,
        deadline_date=job.deadline_date,
    )
    return Response(
        content=ics_data,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="deadline_{job_id[:8]}.ics"'},
    )


@router.get("/calendar/deadlines")
async def all_deadlines(db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .filter(Job.deadline_date.isnot(None))
        .filter(Job.status.notin_(["REJECTED", "WITHDRAWN", "EXPIRED"]))
        .all()
    )
    if not jobs:
        raise HTTPException(status_code=404, detail="No upcoming deadlines")

    from icalendar import Calendar
    cal = Calendar()
    cal.add("prodid", "-//ApplicationVault//EN")
    cal.add("version", "2.0")

    for job in jobs:
        single_ics = generate_job_ics(
            title=job.title,
            organisation=job.organisation,
            url=job.url,
            notes=job.notes,
            deadline_date=job.deadline_date,
        )
        from icalendar import Calendar as CalParser
        parsed = CalParser.from_ical(single_ics)
        for component in parsed.walk():
            if component.name == "VEVENT":
                cal.add_component(component)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="all_deadlines.ics"'},
    )
