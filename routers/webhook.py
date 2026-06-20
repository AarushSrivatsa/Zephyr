from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import PlainTextResponse
from settings import VERIFY_TOKEN

router = APIRouter(prefix='/webhooks', tags=['Webhooks'])

@router.get('')
async def verify_webhook(
    hub_mode: str = Query(alias='hub.mode'),
    hub_challenge: int = Query(alias='hub.challenge'),
    hub_verify_token: str = Query(alias='hub.verify_token')
):
    if hub_mode == 'subscribe' and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=str(hub_challenge))
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Verification failed')

