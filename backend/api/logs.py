from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import ActivityLog, DeliveryLog
from backend.schemas.log import ActivityLogResponse, DeliveryLogResponse

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("", response_model=List[ActivityLogResponse])
@router.get("/", response_model=List[ActivityLogResponse])
def get_logs_root(db: Session = Depends(get_db)):
    return db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(100).all()

@router.get("/activity", response_model=List[ActivityLogResponse])
def get_activity_logs(db: Session = Depends(get_db)):
    return db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(100).all()

@router.get("/delivery", response_model=List[DeliveryLogResponse])
def get_delivery_logs(db: Session = Depends(get_db)):
    return db.query(DeliveryLog).order_by(DeliveryLog.id.desc()).limit(100).all()
