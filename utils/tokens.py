from jwt import encode, decode
from settings import JWT_ACCESS_SECRET, JWT_REFRESH_SECRET
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database.initialization import get_db
from database.models import UserModel, SubscriptionStatus
from sqlalchemy import select
from settings import ACCESS_TOKEN_EXPIRE_HOURS, REFRESH_TOKEN_EXPIRE_DAYS

def create_access_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'type': 'access',
        'exp': datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }
    return encode(payload, JWT_ACCESS_SECRET, algorithm='HS256')

def create_refresh_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'type': 'refresh',
        'exp': datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }
    
    return encode(payload, JWT_REFRESH_SECRET, algorithm='HS256')

def decode_access_token(token: str) -> dict:
    try:
        return decode(token, JWT_ACCESS_SECRET, algorithms=['HS256'])
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Access token expired')
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid access token')

def decode_refresh_token(token: str) -> dict:
    try:
        return decode(token, JWT_REFRESH_SECRET, algorithms=['HS256'])
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token expired')
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')

bearer_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: AsyncSession = Depends(get_db)):
    token = credentials.credentials
    payload = decode_access_token(token)
    
    result = await db.execute(
    select(UserModel)
    .options(selectinload(UserModel.subscription))
    .where(UserModel.user_id == payload['user_id']))
    
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    
    subscription = user.subscription
    
    if not subscription or subscription.next_billing_date < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='No active subscription')

    return user