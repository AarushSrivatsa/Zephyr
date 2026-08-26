from utils.http_client import client
from utils.encryption import decrypt
from database.models import RuleModel, DMLogsModel
from database.initialization import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import random
import asyncio

async def send_dm(ig_user_id: str, comment_id: str, message: str, access_token: str) -> bool:
    response = await client.post(
        f'https://graph.instagram.com/v25.0/{ig_user_id}/messages',
        json={
            'recipient': {'comment_id': comment_id},
            'message': {'text': message}
        },
        params={'access_token': access_token}
    )
    if response.status_code != 200:
        print(f'DM failed: {response.text}')
        return False
    print(f'DM sent for comment {comment_id}')
    return True


async def send_reply(comment_id: str, message: str, access_token: str):
    response = await client.post(
        f'https://graph.instagram.com/v25.0/{comment_id}/replies',
        params={'message': message, 'access_token': access_token}
    )
    if response.status_code != 200:
        print(f'Reply failed: {response.text}')
    else:
        print(f'Reply sent for comment {comment_id}')


async def process_webhook(data: dict, db: AsyncSession):
    try:
        if data.get('object') != 'instagram':
            return

        # Step 1: collect all comments from payload
        comments = []
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') != 'comments':
                    continue
                value = change.get('value', {})
                comment_text = value.get('text', '').strip().lower()
                media_id = value.get('media', {}).get('id')
                comment_id = value.get('id')
                commenter_id = value.get('from', {}).get('id')
                if not all([comment_text, media_id, comment_id, commenter_id]):
                    continue
                comments.append((comment_text, media_id, comment_id, commenter_id))

        if not comments:
            return

        # Step 2: dedupe within payload
        seen_ids = set()
        deduped = []
        for c in comments:
            if c[2] not in seen_ids:
                seen_ids.add(c[2])
                deduped.append(c)
        comments = deduped

        # Step 3: batch duplicate check against DB
        comment_ids = [c[2] for c in comments]
        existing = await db.execute(
            select(DMLogsModel.comment_id)
            .where(DMLogsModel.comment_id.in_(comment_ids))
        )
        duplicate_ids = {row[0] for row in existing.fetchall()}
        comments = [c for c in comments if c[2] not in duplicate_ids]

        if not comments:
            return

        # Step 4: batch fetch matching rules
        media_ids = list({c[1] for c in comments})
        rules_result = await db.execute(
            select(RuleModel)
            .options(selectinload(RuleModel.user))
            .where(
                RuleModel.media_id.in_(media_ids),
                RuleModel.is_active == True
            )
        )
        rules = rules_result.scalars().all()
        rule_map = {(r.media_id, r.catchphrase.lower()): r for r in rules}

        # Step 5: process each comment with delay to avoid spam detection
        for comment_text, media_id, comment_id, commenter_id in comments:
            rule = rule_map.get((media_id, comment_text))
            if not rule:
                print(f'No rule for: {comment_text}')
                continue

            if not rule.user.encrypted_instagram_access_token:
                print(f'Skipping {comment_id}: user {rule.user.user_id} has no token')
                continue

            await asyncio.sleep(60)

            access_token = decrypt(rule.user.encrypted_instagram_access_token)
            message = random.choice(rule.dm_message)

            sent = await send_dm(rule.user.user_id, comment_id, message, access_token)

            if sent:
                if rule.reply_message:
                    await send_reply(comment_id, rule.reply_message, access_token)
                db.add(DMLogsModel(
                    commenter_ig_id=commenter_id,
                    media_id=media_id,
                    comment_id=comment_id,
                    rule_id=rule.id
                ))
                rule.count += 1
                await db.commit()
            else:
                print(f'DM failed for comment {comment_id}, skipping')

    except Exception as e:
        print(f'Webhook processing error: {e}')
        await db.rollback()