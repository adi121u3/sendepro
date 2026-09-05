from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class LeadCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    company: Optional[str] = None
    domain: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None
    sender_name: Optional[str] = None
    sender_full_name: Optional[str] = None

class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    domain: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None
    sender_name: Optional[str] = None
    sender_full_name: Optional[str] = None

class LeadResponse(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    email: str
    company: Optional[str]
    domain: Optional[str]
    position: Optional[str]
    location: Optional[str]
    sender_name: Optional[str]
    sender_full_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
