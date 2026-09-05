from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import pandas as pd
import io
from backend.database import get_db
from backend.models import Lead, ActivityLog
from backend.schemas.lead import LeadCreate, LeadUpdate, LeadResponse

router = APIRouter(prefix="/api/leads", tags=["leads"])

class BulkLeadItem(BaseModel):
    first_name: Optional[str] = "Valued"
    last_name: Optional[str] = "Lead"
    email: str
    company: Optional[str] = ""
    position: Optional[str] = ""
    sender_name: Optional[str] = ""
    sender_full_name: Optional[str] = ""

class BulkLeadRequest(BaseModel):
    leads: List[BulkLeadItem]

@router.get("", response_model=List[LeadResponse])
def get_leads(db: Session = Depends(get_db)):
    return db.query(Lead).order_by(Lead.id.desc()).all()

@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    existing = db.query(Lead).filter(Lead.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A lead with this email address already exists.")
    
    lead = Lead(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        company=payload.company,
        domain=payload.domain,
        position=payload.position,
        location=payload.location,
        sender_name=payload.sender_name,
        sender_full_name=payload.sender_full_name
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

@router.post("/bulk", response_model=List[LeadResponse], status_code=status.HTTP_201_CREATED)
def create_leads_bulk(payload: BulkLeadRequest, db: Session = Depends(get_db)):
    created_leads = []
    new_objects = []
    existing_emails = {row[0] for row in db.query(Lead.email).all()}

    for item in payload.leads:
        email = (item.email or "").strip().lower()
        if not email or "@" not in email or email in existing_emails:
            continue
        existing_emails.add(email) # prevent duplicates within same batch

        lead = Lead(
            first_name=(item.first_name or "Valued").strip(),
            last_name=(item.last_name or "Lead").strip(),
            email=email,
            company=(item.company or "").strip(),
            position=(item.position or "").strip(),
            sender_name=(item.sender_name or "").strip(),
            sender_full_name=(item.sender_full_name or item.sender_name or "").strip()
        )
        new_objects.append(lead)

    if new_objects:
        db.add_all(new_objects)
        db.commit()
        for lead in new_objects:
            db.refresh(lead)
            created_leads.append(lead)

    log = ActivityLog(
        event_type="bulk_leads_imported",
        severity="info",
        message=f"Successfully imported {len(created_leads)} leads in batched transaction.",
        entity_id=None,
        status="SUCCESS"
    )
    db.add(log)
    db.commit()

    return created_leads

@router.post("/import-file", response_model=List[LeadResponse], status_code=status.HTTP_201_CREATED)
async def import_leads_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    filename = file.filename.lower()
    
    try:
        if filename.endswith('.csv') or filename.endswith('.txt'):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    
    df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
    
    email_col = next((c for c in df.columns if 'email' in c), None)
    if not email_col:
        raise HTTPException(status_code=400, detail="Uploaded file must contain an 'email' column.")
        
    first_col = next((c for c in df.columns if 'first' in c or c == 'name'), None)
    last_col = next((c for c in df.columns if 'last' in c), None)
    company_col = next((c for c in df.columns if 'company' in c or 'organization' in c), None)
    position_col = next((c for c in df.columns if 'position' in c or 'title' in c or 'role' in c), None)
    sender_col = next((c for c in df.columns if 'sender' in c), None)

    created_leads = []
    new_objects = []
    existing_emails = {row[0] for row in db.query(Lead.email).all()}

    for _, row in df.iterrows():
        email = str(row.get(email_col, '')).strip().lower()
        if not email or email == 'nan' or '@' not in email or email in existing_emails:
            continue
        existing_emails.add(email)

        full_name = str(row.get(first_col, 'Valued')).strip() if first_col and pd.notna(row.get(first_col)) else 'Valued Lead'
        if not first_col and 'name' in df.columns and pd.notna(row.get('name')):
            full_name = str(row.get('name')).strip()
            
        name_parts = full_name.split(' ')
        f_name = name_parts[0] if name_parts else 'Valued'
        l_name = name_parts[1] if len(name_parts) > 1 else 'Lead'
        if last_col and pd.notna(row.get(last_col)):
            l_name = str(row.get(last_col)).strip()

        comp = str(row.get(company_col, '')).strip() if company_col and pd.notna(row.get(company_col)) else ''
        pos = str(row.get(position_col, '')).strip() if position_col and pd.notna(row.get(position_col)) else ''
        s_name = str(row.get(sender_col, '')).strip() if sender_col and pd.notna(row.get(sender_col)) else ''

        lead = Lead(
            first_name=f_name,
            last_name=l_name,
            email=email,
            company=comp,
            position=pos,
            sender_name=s_name,
            sender_full_name=s_name
        )
        new_objects.append(lead)

    if new_objects:
        db.add_all(new_objects)
        db.commit()
        for lead in new_objects:
            db.refresh(lead)
            created_leads.append(lead)

    log = ActivityLog(
        event_type="file_leads_imported",
        severity="info",
        message=f"Successfully imported {len(created_leads)} leads from file {file.filename}.",
        entity_id=None,
        status="SUCCESS"
    )
    db.add(log)
    db.commit()

    return created_leads

@router.post("/{lead_id}/duplicate", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def duplicate_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    new_email = f"copy_{lead.email}"
    new_lead = Lead(
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=new_email,
        company=lead.company,
        domain=lead.domain,
        position=lead.position,
        location=lead.location,
        sender_name=lead.sender_name,
        sender_full_name=lead.sender_full_name
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    return new_lead

@router.post("/deduplicate", status_code=status.HTTP_200_OK)
def deduplicate_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).all()
    seen_emails = set()
    removed_count = 0
    for lead in leads:
        if lead.email in seen_emails:
            db.delete(lead)
            removed_count += 1
        else:
            seen_emails.add(lead.email)
    db.commit()
    return {"status": "success", "removed_count": removed_count, "message": f"Removed {removed_count} duplicate leads."}

@router.delete("/clear", status_code=status.HTTP_200_OK)
def clear_all_leads(db: Session = Depends(get_db)):
    db.query(Lead).delete()
    db.commit()
    return {"status": "success", "message": "All leads cleared successfully."}

@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if payload.email and payload.email != lead.email:
        existing = db.query(Lead).filter(Lead.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="A lead with this email address already exists.")
        lead.email = payload.email

    if payload.first_name is not None:
        lead.first_name = payload.first_name
    if payload.last_name is not None:
        lead.last_name = payload.last_name
    if payload.company is not None:
        lead.company = payload.company
    if payload.domain is not None:
        lead.domain = payload.domain
    if payload.position is not None:
        lead.position = payload.position
    if payload.location is not None:
        lead.location = payload.location
    if payload.sender_name is not None:
        lead.sender_name = payload.sender_name
    if payload.sender_full_name is not None:
        lead.sender_full_name = payload.sender_full_name

    db.commit()
    db.refresh(lead)
    return lead

@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return None
