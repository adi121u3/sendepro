from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class SettingUpsert(BaseModel):
    key: str
    value: Optional[str] = None

class SettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
