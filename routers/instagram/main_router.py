# routers/instagram/router.py
from fastapi import APIRouter
from routers.instagram import webhook

router = APIRouter(prefix='/instagram', tags=['Instagram'])

router.include_router(webhook.router)
