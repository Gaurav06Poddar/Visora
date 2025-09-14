from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from .database import Base

class Analyzer(Base):
    __tablename__ = "analyzers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    stream_url = Column(String)
    schema_fields = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
