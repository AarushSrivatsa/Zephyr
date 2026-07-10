# routers/instagram/router.py
from fastapi import APIRouter
from routers.instagram.analytics import router as analytics_router
from routers.instagram.webhook import router as webhook_router

router = APIRouter(prefix='/instagram', tags=['Instagram'])

router.include_router(analytics_router)
router.include_router(webhook_router)
