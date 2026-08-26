from fastapi import APIRouter, Query, HTTPException, status, Request, Depends, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from utils.instagram_functions import process_webhook
from settings import VERIFY_TOKEN, CLIENT_SECRET
import hmac
import hashlib
import json

router = APIRouter(prefix='/instagram', tags=['Instagram'])


@router.get('/webhook')
async def verify_webhook(
    hub_mode: str = Query(alias='hub.mode'),
    hub_challenge: int = Query(alias='hub.challenge'),
    hub_verify_token: str = Query(alias='hub.verify_token')
):
    if hub_mode == 'subscribe' and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=str(hub_challenge))
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Verification failed')


@router.post('/webhook')
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    body = await request.body()

    sig_header = request.headers.get('X-Hub-Signature-256', '')
    expected = 'sha256=' + hmac.new(CLIENT_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig_header, expected):
        raise HTTPException(status_code=403, detail='Invalid signature')

    data = json.loads(body)

    if data.get('object') != 'instagram':
        return {'status': 'ignored'}

    background_tasks.add_task(process_webhook, data, db)
    return {'status': 'ok'}