from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
import hashlib
import hmac
import base64
import json
from settings import CLIENT_SECRET

router = APIRouter(prefix='/compliance', tags=['Compliance'])

def verify_signed_request(signed_request: str) -> dict:
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
    
    return data

@router.post('/deletion')
async def data_deletion(request: Request, db: AsyncSession = Depends(get_db)):
    # get signed request from form data
    form_data = await request.form()
    signed_request = form_data.get('signed_request')
    
    if not signed_request:
        raise HTTPException(status_code=400, detail='Missing signed request')
    
    data = verify_signed_request(signed_request)
    
	
    user_id = data.get('user_id')
    if not user_id:
        raise HTTPException(status_code=400, detail='Missing user_id')
    
