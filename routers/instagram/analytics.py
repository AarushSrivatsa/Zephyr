from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from database.models import UserModel
from utils.token_handling import get_current_user
from utils.http_client import client
from utils.encryption import decrypt
from typing import Optional

router = APIRouter(prefix='/analytics')

@router.get('/account')
async def get_account_insights(
    period: str = 'day',
    metric_type: str = 'total_value',
    since: Optional[int] = None,
    until: Optional[int] = None,
    user: UserModel = Depends(get_current_user)
):
    if period not in ('day', 'week', 'month'):
        raise HTTPException(status_code=400, detail='Invalid period')

    access_token = decrypt(user.encrypted_instagram_access_token)

    params = {
        'metric': 'reach,views,accounts_engaged,total_interactions,follows_and_unfollows,shares,saves,likes,comments',
        'period': period,
        'metric_type': metric_type,
        'access_token': access_token
    }
    if since:
        params['since'] = since
    if until:
        params['until'] = until

    response = await client.get(
        f'https://graph.instagram.com/v25.0/{user.user_id}/insights',
        params=params
    )
    return response.json()

@router.get('/media')
async def get_all_media_insights(
    user: UserModel = Depends(get_current_user)
):
    access_token = decrypt(user.encrypted_instagram_access_token)

    # Fetch all media
    media_response = await client.get(
        f'https://graph.instagram.com/v25.0/{user.user_id}/media',
        params={
            'fields': 'id,permalink,media_type',
            'access_token': access_token
        }
    )
    media_list = media_response.json().get('data', [])

    results = []
    for media in media_list:
        if media['media_type'] == 'VIDEO':
            metrics = 'reach,views,likes,comments,saves,shares,total_interactions,ig_reels_avg_watch_time,ig_reels_video_view_total_time,reels_skip_rate,reposts'
        else:
            metrics = 'reach,views,likes,comments,saves,shares,total_interactions,profile_visits,follows,reposts'

        insights_response = await client.get(
            f'https://graph.instagram.com/v25.0/{media["id"]}/insights',
            params={
                'metric': metrics,
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

@router.get('/media/{media_id}')
async def get_media_insights(
    media_id: str,
    media_type: str = 'IMAGE',
    user: UserModel = Depends(get_current_user)
):
    access_token = decrypt(user.encrypted_instagram_access_token)

    if media_type == 'VIDEO':
        metrics = 'reach,views,likes,comments,saves,shares,total_interactions,ig_reels_avg_watch_time,ig_reels_video_view_total_time,reels_skip_rate,reposts'
    else:
        metrics = 'reach,views,likes,comments,saves,shares,total_interactions,profile_visits,follows,reposts'

    response = await client.get(
        f'https://graph.instagram.com/v25.0/{media_id}/insights',
        params={
            'metric': metrics,
            'access_token': access_token
        }
    )
    return response.json()