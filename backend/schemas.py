from pydantic import BaseModel
from typing import List

class AnalyzerBase(BaseModel):
    name: str
    stream_url: str
    schema_fields: List[str]

class AnalyzerCreate(AnalyzerBase):
    name: str
    stream_url: str
    schema_fields: List[str]

class AnalyzerUpdate(BaseModel):
    stream_url: str
    schema_fields: List[str]

class AnalyzerOut(AnalyzerBase):
    id: int

    class Config:
        orm_mode = True
