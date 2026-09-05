from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import Template
from backend.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse

router = APIRouter(prefix="/api/templates", tags=["templates"])

@router.get("", response_model=List[TemplateResponse])
def get_templates(db: Session = Depends(get_db)):
    return db.query(Template).all()

@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)):
    existing = db.query(Template).filter(Template.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template with this name already exists.")
    
    tpl = Template(
        name=payload.name,
        subject=payload.subject,
        body_html=payload.body_html
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tpl)
    db.commit()
    return None
