from pydantic import BaseModel


class JobCreate(BaseModel):
    title: str
    organisation: str | None = None
    url: str | None = None
    location: str | None = None
    salary_range: str | None = None
    deadline_type: str = "unknown"
    deadline_date: str | None = None
    notes: str | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    organisation: str | None = None
    url: str | None = None
    location: str | None = None
    salary_range: str | None = None
    deadline_type: str | None = None
    deadline_date: str | None = None
    status: str | None = None
    notes: str | None = None


class JobResponse(BaseModel):
    id: str
    title: str
    organisation: str | None
    url: str | None
    location: str | None
    salary_range: str | None
    deadline_type: str
    deadline_date: str | None
    status: str
    notes: str | None
    created_at: str
    updated_at: str
    capture_count: int = 0
    event_count: int = 0
    document_count: int = 0
    tags: list[str] = []


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    per_page: int
