from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from settings import CLIENT_ID, REDIRECT_URI
from dependencies import get_db, get_http_client
router = APIRouter(prefix='/authentication',tags=['Authentication'])

@router.get('/login')
async def instagram_login():
    auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=instagram_business_basic,instagram_business_manage_messages,instagram_business_manage_comments"
    )
    return RedirectResponse(auth_url)

@router()
async def instagram_callback(code : str, client = Depends(get_http_client)):
        response = await client.post(
            'https://api.instagram.com/oauth/access_token',
            data={
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'redirect_uri': REDIRECT_URI,
                'code': code
            }
        )
        token_data = response.json()