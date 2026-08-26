from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from database.initialization import get_db
from database.models import SubscriptionModel, UserModel
from utils.dodo_client import dodo
from utils.token_handling import get_current_user_any
from settings import DODO_PRODUCT_ID, DODO_WEBHOOK_SECRET
import hmac, hashlib, base64, json
from datetime import datetime, timezone

router = APIRouter(prefix='/payments', tags=['Payments'])

def _verify_signature(body: bytes, headers, secret: str) -> None:
    msg_id = headers.get('webhook-id', '')
    timestamp = headers.get('webhook-timestamp', '')
    sig_header = headers.get('webhook-signature', '')

    if not all([msg_id, timestamp, sig_header]):
        raise ValueError("Missing webhook headers")

    try:
        ts = int(timestamp)
        now = int(datetime.now(timezone.utc).timestamp())
        if abs(now - ts) > 300:
            raise ValueError("Timestamp too old")
    except (ValueError, TypeError):
        raise ValueError("Bad timestamp")

    secret_bytes = base64.b64decode(secret.removeprefix('whsec_'))
    signed_content = f"{msg_id}.{timestamp}.{body.decode()}"
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed_content.encode(), hashlib.sha256).digest()
    ).decode()

    received = [s.split(',', 1)[1] for s in sig_header.split(' ') if ',' in s]
    if not any(hmac.compare_digest(expected, sig) for sig in received):
        raise ValueError("Signature mismatch")

@router.get('/checkout')
async def create_checkout(
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user_any)
):
    try:
        session = await dodo.checkout_sessions.create(
            product_cart=[{'product_id': DODO_PRODUCT_ID, 'quantity': 1}],
            metadata={'user_id': user.user_id},
            return_url='https://zephyr-m5w7.onrender.com/dashboard'
        )
        return {'url': session.checkout_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/webhook')
async def dodo_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()

    try:
        _verify_signature(body, request.headers, DODO_WEBHOOK_SECRET)
    except ValueError as e:
        print(f"Webhook signature failed: {e}")
        raise HTTPException(status_code=401, detail='Invalid signature')

    payload = json.loads(body)
    print("DODO EVENT:", payload)  # keep this until confirmed working

    event_type = payload.get('type')
    data = payload.get('data', {})
    metadata = data.get('metadata', {})
    user_id = metadata.get('user_id')

    if not user_id:
        return {'status': 'ignored'}

    if event_type in ('subscription.active', 'subscription.renewed'):
        next_billing_date = data.get('next_billing_date')
        if not next_billing_date:
            print(f"No next_billing_date in payload for event {event_type}")
            return {'status': 'ignored'}
        try:
            next_billing_date = datetime.fromisoformat(next_billing_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            print(f"Bad next_billing_date format: {next_billing_date} ({e})")
            raise HTTPException(status_code=400, detail='Invalid next_billing_date')
        await db.execute(
            update(SubscriptionModel)
            .where(SubscriptionModel.user_id == user_id)
            .values(next_billing_date=next_billing_date)
        )
    return {'status': 'ok'}