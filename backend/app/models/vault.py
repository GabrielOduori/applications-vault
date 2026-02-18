from sqlalchemy import Column, Text
from app.database import Base


class VaultConfig(Base):
    __tablename__ = "vault_config"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
