from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_unlocked_vault
from app.models.job import Job

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_unlocked_vault)],
)

_SUBMITTED_STATUSES = ("SUBMITTED", "INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN")


def _pct(num: int, denom: int) -> float | None:
    return round(num / denom * 100, 1) if denom > 0 else None


@router.get("")
async def get_analytics(db: Session = Depends(get_db)):
    # --- Status breakdown ---
    status_rows = (
        db.query(Job.status, func.count(Job.id).label("n"))
        .group_by(Job.status)
        .all()
    )
    by_status: dict[str, int] = {row.status: row.n for row in status_rows}
    total_jobs = sum(by_status.values())

    # --- Submission funnel ---
    # "submitted" = job moved past drafting (current status is SUBMITTED or later)
    submitted_count = sum(by_status.get(s, 0) for s in _SUBMITTED_STATUSES)
    responded_count = sum(by_status.get(s, 0) for s in ("INTERVIEW", "OFFER", "REJECTED"))
    interview_count = sum(by_status.get(s, 0) for s in ("INTERVIEW", "OFFER"))
    offer_count = by_status.get("OFFER", 0)

    # --- Ghost rate: stuck in SUBMITTED with no event for 30+ days ---
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    ghost_row = db.execute(
        text("""
            SELECT COUNT(*) AS n FROM jobs j
            WHERE j.status = 'SUBMITTED'
            AND (SELECT MAX(occurred_at) FROM events WHERE job_id = j.id) < :cutoff
        """),
        {"cutoff": cutoff},
    ).fetchone()
    ghost_count = ghost_row.n if ghost_row else 0

    # --- Avg days SUBMITTED → INTERVIEW ---
    avg_interview_row = db.execute(
        text("""
            SELECT AVG(julianday(i.occurred_at) - julianday(s.occurred_at)) AS avg_days
            FROM events s
            JOIN events i ON i.job_id = s.job_id
                AND i.event_type = 'INTERVIEW'
                AND i.occurred_at > s.occurred_at
            WHERE s.event_type = 'SUBMITTED'
        """)
    ).fetchone()
    avg_days_to_interview = (
        round(avg_interview_row.avg_days, 1)
        if avg_interview_row and avg_interview_row.avg_days is not None
        else None
    )

    # --- Avg days SUBMITTED → decision (OFFER / REJECTED / WITHDRAWN) ---
    avg_decision_row = db.execute(
        text("""
            SELECT AVG(julianday(d.occurred_at) - julianday(s.occurred_at)) AS avg_days
            FROM events s
            JOIN events d ON d.job_id = s.job_id
                AND d.event_type IN ('OFFER', 'REJECTED', 'WITHDRAWN')
                AND d.occurred_at > s.occurred_at
            WHERE s.event_type = 'SUBMITTED'
        """)
    ).fetchone()
    avg_days_to_decision = (
        round(avg_decision_row.avg_days, 1)
        if avg_decision_row and avg_decision_row.avg_days is not None
        else None
    )

    # --- Top orgs with 2+ applications ---
    org_rows = db.execute(
        text("""
            SELECT
                organisation,
                COUNT(*) AS total,
                SUM(CASE WHEN status IN ('INTERVIEW','OFFER','REJECTED') THEN 1 ELSE 0 END) AS responded,
                SUM(CASE WHEN status IN ('INTERVIEW','OFFER') THEN 1 ELSE 0 END) AS interviews,
                SUM(CASE WHEN status = 'OFFER' THEN 1 ELSE 0 END) AS offers
            FROM jobs
            WHERE organisation IS NOT NULL AND organisation != ''
            GROUP BY organisation
            HAVING COUNT(*) >= 2
            ORDER BY total DESC
            LIMIT 10
        """)
    ).fetchall()
    top_orgs = [
        {
            "name": r.organisation,
            "total": r.total,
            "responded": r.responded,
            "interviews": r.interviews,
            "offers": r.offers,
        }
        for r in org_rows
    ]

    return {
        "total_jobs": total_jobs,
        "by_status": by_status,
        "submitted_count": submitted_count,
        "response_rate": _pct(responded_count, submitted_count),
        "interview_rate": _pct(interview_count, submitted_count),
        "offer_rate": _pct(offer_count, submitted_count),
        "ghost_count": ghost_count,
        "ghost_rate": _pct(ghost_count, submitted_count),
        "avg_days_to_interview": avg_days_to_interview,
        "avg_days_to_decision": avg_days_to_decision,
        "top_orgs": top_orgs,
    }
