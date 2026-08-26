from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, delete
from database.initialization import AsyncSessionLocal
from database.models import UserModel
from utils.http_client import client
from utils.encryption import encrypt, decrypt
from datetime import datetime, timezone, timedelta

scheduler = AsyncIOScheduler()

async def refresh_instagram_tokens():
    async with AsyncSessionLocal() as db:
        # find users whose token expires in less than 7 days and are not soft-deleted
        result = await db.execute(
            select(UserModel).where(
                UserModel.instagram_token_expires_at < datetime.now(timezone.utc) + timedelta(days=7),
                UserModel.deleted_at.is_(None),
                UserModel.encrypted_instagram_access_token.isnot(None)
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
                    },
                    timeout=10.0
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
        # bulk DELETE — DB-level CASCADE handles subscriptions, rules, dm_logs, refresh_tokens
        result = await db.execute(
            delete(UserModel).where(
                UserModel.deleted_at.isnot(None),
                UserModel.deleted_at < datetime.now(timezone.utc) - timedelta(days=30)
            )
        )
        await db.commit()
        print(f'Wiped {result.rowcount} deleted users')

async def sync_instagram_profiles():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserModel).where(
                UserModel.deleted_at.is_(None),
                UserModel.encrypted_instagram_access_token.isnot(None)
            )
        )
        users = result.scalars().all()

        for user in users:
            try:
                access_token = decrypt(user.encrypted_instagram_access_token)
                response = await client.get(
                    'https://graph.instagram.com/v25.0/me',
                    params={'fields': 'user_id,username,profile_picture_url', 'access_token': access_token},
                    timeout=10.0
                )
                data = response.json()

                if 'user_id' not in data:
                    print(f'Profile sync failed for {user.user_id}: {data}')
                    continue

                # user_id is our primary key — if Instagram ever returns a
                # different one, don't silently rewrite the PK (that needs a
                # deliberate migration path, not a background job). Just flag it.
                if data['user_id'] != user.user_id:
                    print(f'WARNING: IG user_id mismatch for {user.user_id} -> {data["user_id"]}; skipping')
                    continue

                changed = False
                if data.get('username') and data['username'] != user.username:
                    user.username = data['username']
                    changed = True
                if data.get('profile_picture_url') and data['profile_picture_url'] != user.profile_pic_url:
                    user.profile_pic_url = data['profile_picture_url']
                    changed = True
                if changed:
                    print(f'Profile synced for user {user.user_id}')

            except Exception as e:
                print(f'Profile sync failed for user {user.user_id}: {e}')

        await db.commit()