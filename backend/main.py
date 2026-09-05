import logging
import sys
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import init_db
from backend.api import api_router

# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("email_sender_pro")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Email Sender Pro Backend API with High Priority & Read Receipts"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A 1x1 transparent PNG pixel represented in bytes
TRANSPARENT_PIXEL = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

def log_email_open(email_id: str):
    logger.info(f"Email {email_id} was opened!")
    print(f"DATABASE UPDATE: Email {email_id} status changed to OPENED.")
    try:
        from backend.database import SessionLocal
        from backend.models import ActivityLog
        db = SessionLocal()
        existing_log = db.query(ActivityLog).filter(ActivityLog.provider_message_id == email_id).first()
        if existing_log:
            existing_log.status = "OPENED"
            existing_log.message = f"Email opened (Read Receipt) - Tracking ID: {email_id}"
        
        log = ActivityLog(
            event_type="email_opened",
            severity="info",
            message=f"Email ID {email_id} tracking pixel loaded (Read Receipt). Status updated to OPENED.",
            provider_message_id=email_id,
            status="OPENED"
        )
        db.add(log)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to record email open event in database: {e}")

@app.get("/api/track")
async def track_email(id: str, background_tasks: BackgroundTasks):
    """Tracking endpoint returning 1x1 transparent PNG and logging email open event in background."""
    background_tasks.add_task(log_email_open, id)
    return Response(
        content=TRANSPARENT_PIXEL, 
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.on_event("startup")
def startup_event():
    logger.info("Starting %s backend in %s mode...", settings.app_name, settings.environment)
    init_db()
    logger.info("Database initialization completed.")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Shutting down %s backend...", settings.app_name)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred."}
    )

# Include API routers
app.include_router(api_router)

@app.get("/")
def root():
    return {"message": "Welcome to Email Sender Pro API with High Priority & Read Receipts. Visit /api/health for health status."}
