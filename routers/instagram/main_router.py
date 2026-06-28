# routers/instagram/router.py
from fastapi import APIRouter
from routers.instagram import webhook

router = APIRouter(prefix='/instagram')

router.include_router(webhook.router)
