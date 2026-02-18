from sqlalchemy import Column, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from app.database import Base

job_tags = Table(
    "job_tags",
    Base.metadata,
    Column("job_id", Text, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Text, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    color = Column(Text)

    jobs = relationship("Job", secondary=job_tags, back_populates="tags")
