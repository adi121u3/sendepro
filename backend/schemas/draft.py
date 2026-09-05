from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class DraftCreate(BaseModel):
    from_name: Optional[str] = ""
    subject: Optional[str] = ""
    recipient: Optional[str] = ""
    body: Optional[str] = ""
    attachments: Optional[str] = ""
    sender_account_id: Optional[int] = None

class DraftUpdate(BaseModel):
    from_name: Optional[str] = None
    subject: Optional[str] = None
    recipient: Optional[str] = None
    body: Optional[str] = None
    attachments: Optional[str] = None
    sender_account_id: Optional[int] = None

class DraftResponse(BaseModel):
    id: int
    from_name: Optional[str] = ""
    subject: Optional[str] = ""
    recipient: Optional[str] = ""
    body: Optional[str] = ""
    attachments: Optional[str] = ""
    sender_account_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
