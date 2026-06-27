from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from database.initialization import get_db
from database.models import SubscriptionModel, UserModel
from utils.dodo_client import dodo
from utils.tokens import get_current_user
from settings import DODO_PRODUCT_ID
from datetime import datetime, timezone

router = APIRouter(prefix='/payments', tags=['Payments'])

@router.get('/checkout')
async def create_checkout(user: UserModel = Depends(get_current_user)):
    try:
        session = await dodo.checkout_sessions.create(
            product_cart=[{'product_id': DODO_PRODUCT_ID, 'quantity': 1}],
            metadata={'user_id': user.user_id},
            return_url='https://zephyr-m5w7.onrender.com/dashboard'
        )
        return RedirectResponse(session.checkout_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/webhook')
async def dodo_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        event = dodo.webhooks.unwrap(
            await request.body(),
            headers={
                'webhook-id': request.headers.get('webhook-id', ''),
                'webhook-signature': request.headers.get('webhook-signature', ''),
                'webhook-timestamp': request.headers.get('webhook-timestamp', ''),
            }
        )
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid signature')

    event_type = event.type
    data = event.data
    user_id = data.metadata.get('user_id')

    if not user_id:
        return {'status': 'ignored'}

    if event_type in ('subscription.active', 'subscription.renewed'):
        await db.execute(
            update(SubscriptionModel)
            .where(SubscriptionModel.user_id == user_id)
            .values(next_billing_date=data.next_billing_date)
        )

    return {'status': 'ok'}