from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ActivityLogResponse(BaseModel):
    id: int
    event_type: str
    severity: str
    message: str
    entity_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class DeliveryLogResponse(BaseModel):
    id: int
    campaign_id: Optional[int]
    account_id: Optional[int]
    recipient: str
    provider: str
    status: str
    message_id: Optional[str]
    error_info: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
