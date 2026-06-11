from jwt import encode, decode
from settings import JWT_SECRET, JWT_REFRESH_SECRET
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from database.models import UserModel
from sqlalchemy import select

def create_access_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'type': 'access',
        'exp': datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    return encode(payload, JWT_SECRET, algorithm='HS256')

def create_refresh_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'type': 'refresh',
        'exp': datetime.now(timezone.utc) + timedelta(days=30)
    }
    
    return encode(payload, JWT_REFRESH_SECRET, algorithm='HS256')

def decode_access_token(token: str) -> dict:
    return decode(token, JWT_SECRET, algorithms=['HS256'])

def decode_refresh_token(token: str) -> dict:
    return decode(token, JWT_REFRESH_SECRET, algorithms=['HS256'])

bearer_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: AsyncSession = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token expired')
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

    result = await db.execute(select(UserModel).where(UserModel.user_id == payload['user_id']))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    return user