from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, delete
from database.initialization import AsyncSessionLocal
from database.models import UserModel
from utils.http_client import client
from utils.encryption import encrypt, decrypt
from datetime import datetime, timezone, timedelta
from database.models import DMLogsModel, RuleModel, ScheduledPostModel, PostType, PostStatus
from sqlalchemy.orm import selectinload
from instagram_functions import publish_image, publish_reel, publish_carousel
from cloudflare_client import delete_post_media

scheduler = AsyncIOScheduler()

async def refresh_instagram_tokens():
    async with AsyncSessionLocal() as db:
        # Find users whose token expires in less than 7 days
        result = await db.execute(
            select(UserModel).where(
                UserModel.instagram_token_expires_at < datetime.now(timezone.utc) + timedelta(days=7), UserModel.deleted_at.is_(None)
            )
        )
        users = result.scalars().all()

        for user in users:
            try:
                access_token = decrypt(user.encrypted_instagram_access_token)
                response = await client.get(
                    'https://graph.instagram.com/refresh_access_token',
                    params={
                        'grant_type': 'ig_refresh_token',
                        'access_token': access_token
                    }
                )
                data = response.json()
                new_token = data['access_token']
                expires_in = data['expires_in']

                user.encrypted_instagram_access_token = encrypt(new_token)
                user.instagram_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                print(f'Token refreshed for user {user.user_id}')

            except Exception as e:
                print(f'Token refresh failed for user {user.user_id}: {e}')

        await db.commit()
        
async def wipe_deleted_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserModel).where(
                UserModel.deleted_at.isnot(None),
                UserModel.deleted_at < datetime.now(timezone.utc) - timedelta(days=15)
            )
        )
        users = result.scalars().all()

        for user in users:
            await db.execute(delete(DMLogsModel).where(DMLogsModel.rule_id.in_(
                select(RuleModel.id).where(RuleModel.user_id == user.user_id)
            )))
            await db.execute(delete(RuleModel).where(RuleModel.user_id == user.user_id))

        await db.commit()
        print(f'Wiped {len(users)} deleted users')

async def publish_scheduled_posts():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ScheduledPostModel)
            .options(selectinload(ScheduledPostModel.media_items), selectinload(ScheduledPostModel.user))
            .where(
                ScheduledPostModel.scheduled_at <= datetime.now(timezone.utc),
                ScheduledPostModel.status == PostStatus.pending
            )
        )
        posts = result.scalars().all()

        for post in posts:
            try:
                access_token = decrypt(post.user.encrypted_instagram_access_token)
                
                if post.post_type == PostType.image:
                    await publish_image(post, access_token)
                elif post.post_type == PostType.reel:
                    await publish_reel(post, access_token)
                elif post.post_type == PostType.carousel:
                    await publish_carousel(post, access_token)

                post.status = PostStatus.published
                # Delete from R2
                await delete_post_media(post=post)

            except Exception as e:
                post.status = PostStatus.failed
                post.error_message = str(e)
                print(f'Failed to publish post {post.id}: {e}')

        await db.commit()