from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import Setting
from backend.schemas.setting import SettingUpsert, SettingResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("", response_model=List[SettingResponse])
def get_settings(db: Session = Depends(get_db)):
    return db.query(Setting).all()

@router.post("", response_model=SettingResponse, status_code=status.HTTP_200_OK)
def upsert_setting(payload: SettingUpsert, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == payload.key).first()
    if setting:
        setting.value = payload.value
    else:
        setting = Setting(key=payload.key, value=payload.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
