from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class TemplateCreate(BaseModel):
    name: str
    subject: str
    body_html: str

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None

class TemplateResponse(BaseModel):
    id: int
    name: str
    subject: str
    body_html: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
