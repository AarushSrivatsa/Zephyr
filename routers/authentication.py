from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from settings import CLIENT_ID, REDIRECT_URI, CLIENT_SECRET
from database.initialization import get_db
from utils.http_client import client
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from database.models import UserModel, RefreshTokenModel, SubscriptionModel, SubscriptionStatus
from utils.encryption import encrypt, decrypt
from sqlalchemy import select
from utils.tokens import create_refresh_token, create_access_token, decode_refresh_token
from settings import REFRESH_TOKEN_EXPIRE_DAYS
from sqlalchemy import delete
from fastapi import status
from fastapi.exceptions import HTTPException
from utils.tokens import get_current_user

router = APIRouter(prefix='/authentication',tags=['Authentication'])

@router.get('/login')
async def instagram_login():
    auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=instagram_business_basic%2Cinstagram_business_manage_messages%2Cinstagram_business_manage_comments%2Cinstagram_business_content_publish%2Cinstagram_business_manage_insights"
    )
    
    return RedirectResponse(auth_url)

@router.get('/instagram_callback')
async def instagram_callback(code: str, db : AsyncSession = Depends(get_db)):
    # Step 1: Exchange code for short-lived token
    short_lived_response = await client.post(
        'https://api.instagram.com/oauth/access_token',
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'code': code
        }
    )
    short_lived_data = short_lived_response.json()
    short_lived_token = short_lived_data['access_token']
	
	# Step 2: Exchange for long-lived token
    long_lived_response = await client.get(
        'https://graph.instagram.com/access_token',
        params={
            'grant_type': 'ig_exchange_token',
            'client_secret': CLIENT_SECRET,
            'access_token': short_lived_token
        }
    )

    long_lived_data = long_lived_response.json()
    long_lived_token = long_lived_data['access_token']
    expires_in_seconds = long_lived_data['expires_in']
    
	# Step 3: Fetch user info
    user_response = await client.get(
        'https://graph.instagram.com/v25.0/me',
        params={
            'fields': 'user_id,username,profile_picture_url',
            'access_token': long_lived_token
        }
    )
    user_data = user_response.json()
    
    # Step 4: Encrypt token
    encrypted_token = encrypt(long_lived_token)
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

    # Step 5: Upsert user
    result = await db.execute(select(UserModel).where(UserModel.user_id == user_data['user_id']))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        existing_user.encrypted_instagram_access_token = encrypted_token
        existing_user.instagram_token_expires_at = token_expires_at
        existing_user.username = user_data['username']
        existing_user.profile_pic_url = user_data['profile_picture_url']
    else:
        db.add(UserModel(
            user_id=user_data['user_id'],
            username=user_data['username'],
            profile_pic_url=user_data['profile_picture_url'],
            encrypted_instagram_access_token=encrypted_token,
            instagram_token_expires_at=token_expires_at
        ))
        # Step 6: Create user and subscription if first time user
        db.add(SubscriptionModel(
            user_id=user_data['user_id'],
            next_billing_date=datetime.now(timezone.utc) + timedelta(days=7)
        ))
    
    new_refresh_token = create_refresh_token(user_data['user_id'])
    
    db.add(RefreshTokenModel(
        token=new_refresh_token,
        user_id=user_data['user_id'],
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    ))
    
    await client.post(
    f'https://graph.instagram.com/v25.0/{user_data["user_id"]}/subscribed_apps',
    params={
        'subscribed_fields': 'comments,messages',
        'access_token': long_lived_token
    }
)

    return {
        'access_token': create_access_token(user_data['user_id']),
        'refresh_token': new_refresh_token,
        'token_type': 'bearer'
    }

@router.post('/refresh')
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    
    payload = decode_refresh_token(refresh_token)

    result = await db.execute(select(RefreshTokenModel).where(RefreshTokenModel.token == refresh_token))
    db_token = result.scalar_one_or_none()
    
	# db token not found but someones trying to use it, log user out completely for safety
    if not db_token:
        await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.user_id == payload['user_id']))
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token reuse detected')
    
	# deleting old refresh token
    await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.token == refresh_token))
    
	# creating new refresh token
    new_refresh_token = create_refresh_token(payload['user_id'])
    db.add(RefreshTokenModel(
        token=new_refresh_token,
        user_id=payload['user_id'],
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    ))

    return {
        'access_token': create_access_token(payload['user_id']),
        'refresh_token': new_refresh_token,
        'token_type': 'bearer'
    }

@router.post('/logout')
async def logout(refresh_token: str, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    
    await db.execute(delete(RefreshTokenModel).where(
        RefreshTokenModel.token == refresh_token,
        RefreshTokenModel.user_id == user.user_id
    ))
    
    return {'message': 'Logged out successfully'}