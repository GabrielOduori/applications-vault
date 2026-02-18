from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Text, primary_key=True)
    job_id = Column(Text, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(Text, nullable=False)
    original_filename = Column(Text, nullable=False)
    stored_path = Column(Text, nullable=False, unique=True)
    file_hash = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    version_label = Column(Text)
    mime_type = Column(Text)
    created_at = Column(Text, nullable=False)
    submitted_at = Column(Text, nullable=True)

    job = relationship("Job", back_populates="documents")
