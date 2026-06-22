import re
from database.models import UserModel
from fastapi import HTTPException
from utils.encryption import decrypt
from utils.http_client import client

async def extract_media_id(url: str, user: UserModel) -> str | None:
    # extracting shortcode from link
    pattern = r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)
    shortcode = match.group(1) if match else None
    if not shortcode:
        raise HTTPException(status_code=400, detail='Invalid Instagram URL')
    
	# getting user access token
    access_token = decrypt(user.encrypted_instagram_access_token)
    
    next_url = f'https://graph.instagram.com/v25.0/{user.user_id}/media'
    params = {
        'fields': 'id,permalink',
        'access_token': access_token
    }
    
    while next_url:
        response = await client.get(next_url, params=params)
        data = response.json()

        for media in data.get('data', []):
            if shortcode in media.get('permalink', ''):
                return {
                    'media_id': media['id'],
                    'permalink': media['permalink']
                }

        next_url = data.get('paging', {}).get('next')
        params = {}

    raise HTTPException(status_code=404, detail='Post not found on your Instagram account')
	


    
	
    
