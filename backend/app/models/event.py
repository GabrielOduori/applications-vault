from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Text, primary_key=True)
    job_id = Column(Text, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(Text, nullable=False)
    notes = Column(Text)
    next_action_date = Column(Text)
    occurred_at = Column(Text, nullable=False)

    job = relationship("Job", back_populates="events")
