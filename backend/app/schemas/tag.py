from pydantic import BaseModel


class TagCreate(BaseModel):
    name: str
    color: str | None = None


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class TagResponse(BaseModel):
    id: str
    name: str
    color: str | None
    job_count: int = 0
