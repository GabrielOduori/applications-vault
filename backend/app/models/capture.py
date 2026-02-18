from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Capture(Base):
    __tablename__ = "captures"

    id = Column(Text, primary_key=True)
    job_id = Column(Text, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text)
    page_title = Column(Text)
    text_snapshot = Column(Text)
    html_path = Column(Text)
    pdf_path = Column(Text)
    capture_method = Column(Text, nullable=False)
    captured_at = Column(Text, nullable=False)

    job = relationship("Job", back_populates="captures")
