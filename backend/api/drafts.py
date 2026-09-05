from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from backend.database import get_db
from backend.models import Draft, ActivityLog
from backend.schemas.draft import DraftCreate, DraftUpdate, DraftResponse

router = APIRouter(prefix="/api/drafts", tags=["drafts"])

@router.get("", response_model=List[DraftResponse])
def get_drafts(db: Session = Depends(get_db)):
    drafts = db.query(Draft).order_by(Draft.updated_at.desc()).all()
    return drafts

@router.post("", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
def create_draft(payload: DraftCreate, db: Session = Depends(get_db)):
    draft = Draft(
        from_name=payload.from_name or "",
        subject=payload.subject or "",
        recipient=payload.recipient or "",
        body=payload.body or "",
        attachments=payload.attachments or "",
        sender_account_id=payload.sender_account_id
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    log = ActivityLog(
        event_type="draft_created",
        severity="info",
        message=f"Draft #{draft.id} ('{draft.subject or 'Untitled'}') created.",
        entity_id=draft.id
    )
    db.add(log)
    db.commit()

    return draft

@router.put("/{draft_id}", response_model=DraftResponse)
def update_draft(draft_id: int, payload: DraftUpdate, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if payload.from_name is not None:
        draft.from_name = payload.from_name
    if payload.subject is not None:
        draft.subject = payload.subject
    if payload.recipient is not None:
        draft.recipient = payload.recipient
    if payload.body is not None:
        draft.body = payload.body
    if payload.attachments is not None:
        draft.attachments = payload.attachments
    if payload.sender_account_id is not None:
        draft.sender_account_id = payload.sender_account_id

    draft.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)

    return draft

@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    db.delete(draft)
    db.commit()

    log = ActivityLog(
        event_type="draft_deleted",
        severity="info",
        message=f"Draft #{draft_id} deleted.",
        entity_id=draft_id
    )
    db.add(log)
    db.commit()

    return None
