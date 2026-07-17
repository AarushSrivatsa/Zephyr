# routers/instagram/router.py
from fastapi import APIRouter
from routers.instagram.analytics import router as analytics_router
from routers.instagram.webhook import router as webhook_router
from routers.instagram.post_scheduler import router as posts_router

router = APIRouter(prefix='/instagram', tags=['Instagram'])

router.include_router(webhook_router)