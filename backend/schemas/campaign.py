from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str
    tag: Optional[str] = "Marketing"
    template_id: Optional[int] = None
    template_ids: Optional[List[int]] = []
    account_id: Optional[int] = None
    lead_ids: Optional[List[int]] = []
    delay_seconds: Optional[int] = 30
    jitter_seconds: Optional[int] = 2
    max_retries: Optional[int] = 3
    rotation_mode: Optional[str] = "round_robin"
    reply_to: Optional[str] = None
    delivery_route: Optional[str] = "auto"


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    tag: Optional[str] = None
    template_id: Optional[int] = None
    template_ids: Optional[List[int]] = None
    account_id: Optional[int] = None
    delay_seconds: Optional[int] = None
    jitter_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    rotation_mode: Optional[str] = None
    reply_to: Optional[str] = None
    delivery_route: Optional[str] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    status: str
    tag: str = "Marketing"
    template_id: Optional[int] = None
    template_ids: List[int] = Field(default_factory=list)
    account_id: Optional[int] = None
    delay_seconds: int = 30
    jitter_seconds: int = 2
    max_retries: int = 3
    rotation_mode: str = "round_robin"
    reply_to: Optional[str] = None
    delivery_route: str = "auto"
    total_recipients: int = 0
    sent_count: int = 0
    failed_count: int = 0
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_orm(cls, obj):
        data = {
            "id": obj.id,
            "name": obj.name,
            "status": obj.status or "draft",
            "tag": getattr(obj, "tag", None) or "Marketing",
            "template_id": obj.template_id,
            "account_id": obj.account_id,
            "delay_seconds": int(getattr(obj, "delay_seconds", None) or 30),
            "jitter_seconds": int(getattr(obj, "jitter_seconds", None) or 0),
            "max_retries": int(getattr(obj, "max_retries", None) or 3),
            "rotation_mode": getattr(obj, "rotation_mode", None) or "round_robin",
            "reply_to": getattr(obj, "reply_to", None),
            "delivery_route": getattr(obj, "delivery_route", None) or "auto",
            "total_recipients": int(obj.total_recipients or 0),
            "sent_count": int(obj.sent_count or 0),
            "failed_count": int(obj.failed_count or 0),
            "started_at": obj.started_at,
            "paused_at": obj.paused_at,
            "completed_at": obj.completed_at,
            "stopped_at": obj.stopped_at,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "template_ids": [],
        }
        if hasattr(obj, "templates") and obj.templates:
            data["template_ids"] = [t.id for t in obj.templates]
        elif obj.template_id:
            data["template_ids"] = [obj.template_id]
        return cls(**data)

    class Config:
        from_attributes = True
