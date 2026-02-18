from pydantic import BaseModel


class SearchResult(BaseModel):
    job_id: str
    job_title: str
    organisation: str | None
    source: str  # "job" or "capture"
    snippet: str
    rank: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str
