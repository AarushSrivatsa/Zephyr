from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from database.models import UserModel, ScheduledPostModel, ScheduledPostMediaModel, PostType, PostStatus
from utils.token_handling import get_current_user
from utils.cloudflare_client import upload_file
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from utils.cloudflare_client import delete_post_media

router = APIRouter(prefix='/posts', tags=['Scheduled Posts'])

class ScheduledPostMediaResponse(BaseModel):
    id : int
    media_url : str
    media_type : str
    order : int

    class Config:
        from_attributes = True

class ScheduledPostResponse(BaseModel):
    id: int
    caption: Optional[str]
    post_type: PostType
    status: PostStatus
    scheduled_at: datetime
    created_at: datetime
    error_message: Optional[str]
    media_items : list[ScheduledPostMediaResponse]

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
        url, key = await upload_file(user.user_id,file.filename, file_bytes, file.content_type)
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

    result = await db.execute(
    select(ScheduledPostModel)
    .options(selectinload(ScheduledPostModel.media_items))
    .where(ScheduledPostModel.id == new_post.id)
)
    return result.scalar_one()

@router.get('', response_model=list[ScheduledPostResponse])
async def list_scheduled_posts(
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ScheduledPostModel)
        .options(selectinload(ScheduledPostModel.media_items))
        .where(ScheduledPostModel.user_id == user.user_id)
        .order_by(ScheduledPostModel.scheduled_at)
    )
    return result.scalars().all()


@router.get('/{post_id}', response_model=ScheduledPostResponse)
async def get_scheduled_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ScheduledPostModel)
        .options(selectinload(ScheduledPostModel.media_items))
        .where(ScheduledPostModel.id == post_id, ScheduledPostModel.user_id == user.user_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail='Post not found')
    return post

@router.patch('/{post_id}', response_model=ScheduledPostResponse)
async def update_scheduled_post(
    post_id: int,
    caption: Optional[str] = Form(None),
    scheduled_at: Optional[datetime] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ScheduledPostModel)
        .where(ScheduledPostModel.id == post_id, ScheduledPostModel.user_id == user.user_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail='Post not found')

    if post.status != PostStatus.pending:
        raise HTTPException(status_code=400, detail='Cannot edit a published or failed post')

    if caption is not None:
        post.caption = caption
    if scheduled_at is not None:
        if scheduled_at < datetime.now(scheduled_at.tzinfo):
            raise HTTPException(status_code=400, detail='Scheduled time must be in the future')
        post.scheduled_at = scheduled_at

    await db.flush()

    result = await db.execute(
    select(ScheduledPostModel)
    .options(selectinload(ScheduledPostModel.media_items))
    .where(ScheduledPostModel.id == post.id,
    ScheduledPostModel.user_id == user.user_id
        )
    )

    return result.scalar_one()

@router.delete('/{post_id}')
async def delete_scheduled_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ScheduledPostModel)
        .options(selectinload(ScheduledPostModel.media_items))
        .where(ScheduledPostModel.id == post_id, ScheduledPostModel.user_id == user.user_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail='Post not found')

    await delete_post_media(post)
    await db.delete(post)
    return {'message': 'Post deleted successfully'}