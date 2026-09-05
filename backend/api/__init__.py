from fastapi import APIRouter, Depends
from backend.api import health, accounts, leads, templates, campaigns, logs, settings, drafts, send, oauth
from backend.security import auth
from backend.security.auth import get_current_admin

api_router = APIRouter()
api_router.include_router(health.router, prefix="", tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(oauth.router)
api_router.include_router(accounts.router, dependencies=[Depends(get_current_admin)])
api_router.include_router(leads.router, dependencies=[Depends(get_current_admin)])
api_router.include_router(templates.router, dependencies=[Depends(get_current_admin)])
api_router.include_router(campaigns.router, dependencies=[Depends(get_current_admin)])
api_router.include_router(logs.router, dependencies=[Depends(get_current_admin)])
api_router.include_router(settings.router, dependencies=[Depends(get_current_admin)])
api_router.include_router(drafts.router, dependencies=[Depends(get_current_admin)])
api_router.include_router(send.router, dependencies=[Depends(get_current_admin)])
