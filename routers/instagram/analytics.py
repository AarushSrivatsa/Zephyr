from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from database.models import UserModel
from utils.token_handling import get_current_user
from utils.http_client import client
from utils.encryption import decrypt

router = APIRouter(prefix='/analytics', tags=['Analytics'])

@router.get('/account')
async def get_account_insights(
    period: str = 'day',
    user: UserModel = Depends(get_current_user)
):
    if period not in ('day', 'week', 'month'):
        raise HTTPException(status_code=400, detail='Invalid period. Use day, week or month')
    
    access_token = decrypt(user.encrypted_instagram_access_token)
    
    response = await client.get(
        f'https://graph.instagram.com/v25.0/{user.user_id}/insights',
        params={
            'metric': 'impressions,reach,profile_views',
            'period': period,
            'access_token': access_token
        }
    )
    return response.json()

@router.get('/posts')
async def get_all_posts_insights(
    user: UserModel = Depends(get_current_user)
):
    access_token = decrypt(user.encrypted_instagram_access_token)

    # Fetch all media first
    media_response = await client.get(
        f'https://graph.instagram.com/v25.0/{user.user_id}/media',
        params={
            'fields': 'id,permalink,media_type',
            'access_token': access_token
        }
    )
    media_list = media_response.json().get('data', [])

    # Fetch insights for each post
    results = []
    for media in media_list:
        insights_response = await client.get(
            f'https://graph.instagram.com/v25.0/{media["id"]}/insights',
            params={
                'metric': 'engagement,impressions,reach',
                'access_token': access_token
            }
        )
        results.append({
            'media_id': media['id'],
            'permalink': media['permalink'],
            'media_type': media['media_type'],
            'insights': insights_response.json().get('data', [])
        })

    return results

@router.get('/post/{media_id}')
async def get_post_insights(
    media_id: str,
    user: UserModel = Depends(get_current_user)
):
    access_token = decrypt(user.encrypted_instagram_access_token)

    response = await client.get(
        f'https://graph.instagram.com/v25.0/{media_id}/insights',
        params={
            'metric': 'engagement,impressions,reach',
            'access_token': access_token
        }
    )
    return response.json()