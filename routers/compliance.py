from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from sqlalchemy import delete, update, select
from database.models import UserModel, RuleModel, DMLogsModel, RefreshTokenModel
from datetime import datetime, timezone
import hashlib
import hmac
import base64
import json
from settings import CLIENT_SECRET

router = APIRouter(prefix='/compliance', tags=['Compliance'])

@router.post('/deletion')
async def data_deletion(request: Request, db: AsyncSession = Depends(get_db)):
    # get signed request from form data
    form_data = await request.form()
    signed_request = form_data.get('signed_request')
    
    if not signed_request:
        raise HTTPException(status_code=400, detail='Missing signed request')
    
    encoded_sig, payload = signed_request.split('.')
    
    # Fix padding
    encoded_sig += '=' * ((4 - len(encoded_sig) % 4) % 4)
    payload_padded = payload + '=' * ((4 - len(payload) % 4) % 4)
    
    # Decode
    sig = base64.urlsafe_b64decode(encoded_sig)
    data = json.loads(base64.urlsafe_b64decode(payload_padded))
    
    # Verify signature using original unpadded payload
    expected_sig = hmac.new(
        CLIENT_SECRET.encode('ascii'),
        payload.encode('ascii'),
        hashlib.sha256
    ).digest()
    
    if not hmac.compare_digest(expected_sig, sig):
        raise HTTPException(status_code=403, detail='Invalid signature')
    
    user_id = data.get('user_id')
    if not user_id:
        raise HTTPException(status_code=400, detail='Missing user_id')
    
    # Revoke all sessions
    await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id))

    # Mark as deleted
    await db.execute(
        update(UserModel)
        .where(UserModel.user_id == user_id)
        .values(
            encrypted_instagram_access_token=None,
            deleted_at=datetime.now(timezone.utc)
        )
    )

    confirmation_code = f'zephyr_{user_id}_{int(datetime.now().timestamp())}'
    return {
        'url': f'https://zephyr-m5w7.onrender.com/compliance/deletion-status?code={confirmation_code}',
        'confirmation_code': confirmation_code
    }

@router.get('/deletion-status')
async def deletion_status(code: str, db: AsyncSession = Depends(get_db)):
    try:
        user_id = code.split('_')[1]
    except:
        raise HTTPException(status_code=400, detail='Invalid code')

    result = await db.execute(select(UserModel).where(UserModel.user_id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.deleted_at:
        raise HTTPException(status_code=404, detail='No deletion request found')

    return {'code': code, 'status': 'deleted', 'deleted_at': user.deleted_at}