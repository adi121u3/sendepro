from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class CampaignCreate(BaseModel):
    name: str
    tag: Optional[str] = "Marketing"
    template_id: Optional[int] = None
    template_ids: Optional[List[int]] = []
    account_id: Optional[int] = None
    lead_ids: Optional[List[int]] = []

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    tag: Optional[str] = None
    template_id: Optional[int] = None
    template_ids: Optional[List[int]] = None
    account_id: Optional[int] = None

class CampaignResponse(BaseModel):
    id: int
    name: str
    status: str
    tag: str = "Marketing"
    template_id: Optional[int]
    template_ids: List[int] = []
    account_id: Optional[int]
    total_recipients: int
    sent_count: int
    failed_count: int
    started_at: Optional[datetime]
    paused_at: Optional[datetime]
    completed_at: Optional[datetime]
    stopped_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, obj):
        res = super().from_orm(obj)
        if hasattr(obj, 'templates') and obj.templates:
            res.template_ids = [t.id for t in obj.templates]
        elif obj.template_id:
            res.template_ids = [obj.template_id]
        return res

    class Config:
        from_attributes = True
