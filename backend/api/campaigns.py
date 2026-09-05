from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from backend.database import get_db
from backend.models import Campaign, CampaignRecipient, ActivityLog, Template
from backend.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from backend.campaign.engine import CampaignEngine

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

@router.get("", response_model=List[CampaignResponse])
def get_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).order_by(Campaign.id.desc()).all()
    return [CampaignResponse.from_orm(c) for c in campaigns]

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    total_recipients = len(payload.lead_ids) if payload.lead_ids else 0
    campaign = Campaign(
        name=payload.name,
        tag=payload.tag or "Marketing",
        status="draft",
        template_id=payload.template_id,
        account_id=payload.account_id,
        total_recipients=total_recipients,
        sent_count=0,
        failed_count=0
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Handle multiple templates for A/B testing
    templates_list = []
    if payload.template_ids:
        templates_list = db.query(Template).filter(Template.id.in_(payload.template_ids)).all()
    elif payload.template_id:
        t_obj = db.query(Template).filter(Template.id == payload.template_id).first()
        if t_obj:
            templates_list = [t_obj]

    if templates_list:
        campaign.templates = templates_list
        if not campaign.template_id:
            campaign.template_id = templates_list[0].id
        db.commit()

    # Queue recipients
    if payload.lead_ids:
        for lead_id in payload.lead_ids:
            recipient = CampaignRecipient(
                campaign_id=campaign.id,
                lead_id=lead_id,
                status="queued"
            )
            db.add(recipient)
        db.commit()

    log = ActivityLog(
        event_type="campaign_created",
        severity="info",
        message=f"Campaign '{campaign.name}' created with {total_recipients} recipients and {len(templates_list)} templates (A/B testing).",
        entity_id=campaign.id
    )
    db.add(log)
    db.commit()

    return CampaignResponse.from_orm(campaign)

@router.api_route("/{campaign_id}/status", methods=["PATCH", "POST"], response_model=CampaignResponse)
async def update_campaign_status(campaign_id: int, request: Request, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    
    new_status = body.get("status") or request.query_params.get("status")
    if not new_status or new_status not in ["draft", "running", "paused", "completed", "stopped"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    campaign.status = new_status
    if new_status == "running":
        if not campaign.started_at:
            campaign.started_at = datetime.utcnow()
        CampaignEngine.start_campaign(campaign.id)
    elif new_status == "paused":
        campaign.paused_at = datetime.utcnow()
    elif new_status == "completed":
        campaign.completed_at = datetime.utcnow()
    elif new_status == "stopped":
        campaign.stopped_at = datetime.utcnow()

    db.commit()
    db.refresh(campaign)

    log = ActivityLog(
        event_type=f"campaign_{new_status}",
        severity="info",
        message=f"Campaign '{campaign.name}' status updated to {new_status}.",
        entity_id=campaign.id
    )
    db.add(log)
    db.commit()

    return CampaignResponse.from_orm(campaign)
