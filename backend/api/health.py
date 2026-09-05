from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from backend.schemas import HealthResponse
from backend.config import settings
import logging

logger = logging.getLogger("email_sender_pro.api.health")

router = APIRouter()

@router.get("/api/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Database health check failed: %s", str(e))
        db_status = "error"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "service": settings.app_name,
        "database": db_status,
        "environment": settings.environment
    }
