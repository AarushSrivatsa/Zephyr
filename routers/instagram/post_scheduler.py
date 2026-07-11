from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from database.models import UserModel, ScheduledPostModel, ScheduledPostMediaModel, PostType, PostStatus
from utils.token_handling import get_current_user
from utils.cloudflare_client import upload_file, generate_key
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

router = APIRouter(prefix='/posts', tags=['Scheduled Posts'])

class ScheduledPostResponse(BaseModel):
    id: int
    caption: Optional[str]
    post_type: PostType
    status: PostStatus
    scheduled_at: datetime
    created_at: datetime
    error_message: Optional[str]

    class Config:
        from_attributes = True

@router.post('', response_model=ScheduledPostResponse)
async def create_scheduled_post(
    caption: Optional[str] = Form(None),
    post_type: str = Form(...), # form means its required
    scheduled_at: datetime = Form(...),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    if not files:
        raise HTTPException(status_code=400, detail='At least one file is required')

    if post_type == 'carousel' and len(files) < 2:
        raise HTTPException(status_code=400, detail='Carousel requires at least 2 files')

    if post_type == 'carousel' and len(files) > 10:
        raise HTTPException(status_code=400, detail='Carousel supports maximum 10 files')

    if scheduled_at.minute != 0 or scheduled_at.second != 0:
        raise HTTPException(status_code=400, detail='Scheduled time must be on the hour')

    if scheduled_at < datetime.now(scheduled_at.tzinfo):
        raise HTTPException(status_code=400, detail='Scheduled time must be in the future')

    # Upload files to R2
    uploaded_media = []
    for i, file in enumerate(files):
        file_bytes = await file.read()
        key = generate_key(user.user_id, file.filename)
        url = await upload_file(file_bytes, key, file.content_type)
        uploaded_media.append({
            'url': url,
            'key': key,
            'content_type': file.content_type,
            'order': i
        })

    # Create scheduled post
    new_post = ScheduledPostModel(
        caption=caption,
        post_type=PostType[post_type],
        scheduled_at=scheduled_at,
        user_id=user.user_id
    )
    db.add(new_post)
    await db.flush()

    # Add media items
    for media in uploaded_media:
        db.add(ScheduledPostMediaModel(
            media_url=media['url'],
            media_type=media['content_type'],
            order=media['order'],
            post_id=new_post.id
        ))

    await db.flush()
    await db.refresh(new_post)
    return new_post
