from pydantic import BaseModel


class EventCreate(BaseModel):
    event_type: str
    notes: str | None = None
    next_action_date: str | None = None


class EventResponse(BaseModel):
    id: str
    job_id: str
    event_type: str
    notes: str | None
    next_action_date: str | None
    occurred_at: str
