from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from settings import CLIENT_ID, REDIRECT_URI, CLIENT_SECRET
from database.initialization import get_db
from utils.http_client import client
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from database.models import UserModel, RefreshTokenModel, SubscriptionModel
from utils.encryption import encrypt, decrypt
from sqlalchemy import select
from utils.token_handling import create_refresh_token, create_access_token, decode_refresh_token
from settings import REFRESH_TOKEN_EXPIRE_DAYS
from sqlalchemy import delete
from fastapi import status
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from utils.token_handling import get_current_user, get_current_user_any

router = APIRouter(prefix='/user', tags=['User'])

@router.get('/login')
async def instagram_login():
    auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=instagram_business_basic%2Cinstagram_business_manage_messages%2Cinstagram_business_manage_comments"
    )
    return RedirectResponse(auth_url)

@router.get('/instagram_callback')
async def instagram_callback(code: str, db: AsyncSession = Depends(get_db)):
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

    print("STATUS:", short_lived_response.status_code)
    print("META RESPONSE:", short_lived_data)

    if 'access_token' not in short_lived_data:
        raise HTTPException(
            status_code=400,
            detail=f"Instagram token exchange failed: {short_lived_data}"
        )

    short_lived_token = short_lived_data['access_token']

    # Step 2: Exchange for long-lived token
    long_lived_response = await client.post(
        'https://graph.instagram.com/access_token',
        data={
            'grant_type': 'ig_exchange_token',
            'client_secret': CLIENT_SECRET,
            'access_token': short_lived_token
        }
    )
    long_lived_data = long_lived_response.json()

    if 'access_token' not in long_lived_data:
        raise HTTPException(status_code=400, detail=f"Long-lived token exchange failed: {long_lived_data}")
    long_lived_token = long_lived_data['access_token']

    expires_in_seconds = long_lived_data.get('expires_in', 5184000)  # fallback ~60 days if missing

    expires_in_seconds = long_lived_data['expires_in']

    # Step 3: Fetch user info
    user_response = await client.get(
        'https://graph.instagram.com/v25.0/me',
        data={
            'fields': 'user_id,username,profile_picture_url',
            'access_token': long_lived_token
        }
    )
    user_data = user_response.json()
    if 'user_id' not in user_data:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Instagram profile: {user_data}")

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
        existing_user.deleted_at = None  # restore soft-deleted accounts
    else:
        db.add(UserModel(
            user_id=user_data['user_id'],
            username=user_data['username'],
            profile_pic_url=user_data['profile_picture_url'],
            encrypted_instagram_access_token=encrypted_token,
            instagram_token_expires_at=token_expires_at
        ))
        # Only create subscription for brand-new users
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

    # Step 6: Subscribe to Instagram webhook events
# wrap it
    try:
        sub_response = await client.post(
            f'https://graph.instagram.com/v25.0/{user_data["user_id"]}/subscribed_apps',
            params={
                'subscribed_fields': 'comments,messages',
                'access_token': long_lived_token
            }
        )
        print(f'Webhook subscription response: {sub_response.status_code} {sub_response.text}')
    except Exception as e:
        print(f'Webhook subscription failed: {e}')

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

    # token not in DB but someone's using it — log out everywhere for safety
    if not db_token:
        await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.user_id == payload['user_id']))
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token reuse detected')

    # rotate: delete old, issue new
    await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.token == refresh_token))

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
async def logout(refresh_token: str, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user_any)):
    await db.execute(delete(RefreshTokenModel).where(
        RefreshTokenModel.token == refresh_token,
        RefreshTokenModel.user_id == user.user_id
    ))
    return {'message': 'Logged out successfully'}

class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    profile_pic_url: str

    class Config:
        from_attributes = True

@router.get('/me', response_model=UserProfileResponse)
async def get_me(user: UserModel = Depends(get_current_user_any)):
    # Deliberately uses get_current_user_any (not get_current_user) — profile
    # info should be visible even if the subscription has lapsed, since the
    # rail/account UI needs it regardless of billing state.
    return user

@router.delete('/me')
async def delete_account(db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user_any)):
    # Unsubscribe from Instagram webhooks
    access_token = decrypt(user.encrypted_instagram_access_token)
    try:
        await client.delete(
            f'https://graph.instagram.com/v25.0/{user.user_id}/subscribed_apps',
            params={'access_token': access_token}
        )
    except Exception as e:
        print(f'Webhook unsubscribe failed: {e}')

    # Revoke all sessions
    await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.user_id == user.user_id))

    # Soft-delete: clear token, mark deleted — background job purges after 15 days
    user.encrypted_instagram_access_token = None
    user.deleted_at = datetime.now(timezone.utc)

    return {'message': 'Account deleted successfully'}