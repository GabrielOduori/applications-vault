from sqlalchemy import Column, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    organisation = Column(Text)
    url = Column(Text)
    location = Column(Text)
    salary_range = Column(Text)
    deadline_type = Column(Text, default="unknown")
    deadline_date = Column(Text)
    status = Column(Text, nullable=False, default="SAVED")
    notes = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    captures = relationship("Capture", back_populates="job", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="job", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="job", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="job_tags", back_populates="jobs")
