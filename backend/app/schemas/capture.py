from pydantic import BaseModel


class CaptureCreate(BaseModel):
    url: str | None = None
    page_title: str | None = None
    text_snapshot: str | None = None
    html_content: str | None = None
    capture_method: str = "manual_paste"


class CaptureResponse(BaseModel):
    id: str
    job_id: str
    url: str | None
    page_title: str | None
    text_snapshot: str | None
    html_path: str | None
    pdf_path: str | None
    capture_method: str
    captured_at: str


class QuickCaptureRequest(BaseModel):
    url: str | None = None
    page_title: str | None = None
    text_snapshot: str | None = None
    html_content: str | None = None
    capture_method: str = "generic_html"
    title: str | None = None
    organisation: str | None = None
    location: str | None = None
    deadline: str | None = None  # e.g. "March 15, 2026" or "2026-03-15"


class QuickCaptureResponse(BaseModel):
    job: "JobResponse"
    capture: CaptureResponse


from app.schemas.job import JobResponse
QuickCaptureResponse.model_rebuild()
