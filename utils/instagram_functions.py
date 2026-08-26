from utils.http_client import client
from utils.encryption import decrypt
from database.models import RuleModel, DMLogsModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import random
import asyncio


async def send_dm(ig_user_id: str, comment_id: str, message: str, access_token: str) -> bool:
    try:
        response = await client.post(
            f'https://graph.instagram.com/v25.0/{ig_user_id}/messages',
            json={
                'recipient': {'comment_id': comment_id},
                'message': {'text': message}
            },
            params={'access_token': access_token}
        )
        print(f'send_dm status: {response.status_code}, body: {response.text}')
        if response.status_code != 200:
            print(f'DM failed for comment {comment_id}: {response.text}')
            return False
        print(f'DM sent for comment {comment_id}')
        return True
    except Exception as e:
        print(f'send_dm exception for comment {comment_id}: {e}')
        return False


async def send_reply(comment_id: str, message: str, access_token: str):
    try:
        response = await client.post(
            f'https://graph.instagram.com/v25.0/{comment_id}/replies',
            params={'message': message, 'access_token': access_token}
        )
        print(f'send_reply status: {response.status_code}, body: {response.text}')
        if response.status_code != 200:
            print(f'Reply failed for comment {comment_id}: {response.text}')
        else:
            print(f'Reply sent for comment {comment_id}')
    except Exception as e:
        print(f'send_reply exception for comment {comment_id}: {e}')


async def process_webhook(data: dict, db: AsyncSession):
    try:
        print(f'process_webhook called with object: {data.get("object")}')

        if data.get('object') != 'instagram':
            print('Ignoring non-instagram webhook')
            return

        # Step 1: collect all comments from payload.
        # comment_text keeps its ORIGINAL case — we lower() it wherever
        # needed instead of storing a second lowercased copy.
        comments = []
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                print(f'Processing change field: {change.get("field")}')
                if change.get('field') != 'comments':
                    continue
                value = change.get('value', {})
                comment_text = value.get('text', '').strip()
                media_id = value.get('media', {}).get('id')
                comment_id = value.get('id')
                commenter_id = value.get('from', {}).get('id')
                print(f'Comment: text={comment_text}, media_id={media_id}, comment_id={comment_id}, commenter_id={commenter_id}')
                if not all([comment_text, media_id, comment_id, commenter_id]):
                    print(f'Skipping comment — missing fields')
                    continue
                comments.append((comment_text, media_id, comment_id, commenter_id))

        print(f'Total comments collected: {len(comments)}')

        if not comments:
            print('No comments to process')
            return

        # Step 2: dedupe within payload
        seen_ids = set()
        deduped = []
        for c in comments:
            if c[2] not in seen_ids:
                seen_ids.add(c[2])
                deduped.append(c)
        comments = deduped
        print(f'After dedup: {len(comments)} comments')

        # Step 3: batch duplicate check against DB
        comment_ids = [c[2] for c in comments]
        existing = await db.execute(
            select(DMLogsModel.comment_id)
            .where(DMLogsModel.comment_id.in_(comment_ids))
        )
        duplicate_ids = {row[0] for row in existing.fetchall()}
        print(f'Duplicate comment_ids already in DB: {duplicate_ids}')
        comments = [c for c in comments if c[2] not in duplicate_ids]
        print(f'After DB dedupe: {len(comments)} comments')

        if not comments:
            print('All comments already processed')
            return

        # Step 4: batch fetch matching rules
        media_ids = list({c[1] for c in comments})
        print(f'Fetching rules for media_ids: {media_ids}')
        rules_result = await db.execute(
            select(RuleModel)
            .options(selectinload(RuleModel.user))
            .where(
                RuleModel.media_id.in_(media_ids),
                RuleModel.is_active == True
            )
        )
        rules = rules_result.scalars().all()
        print(f'Rules found: {len(rules)}')

        # Always key on the lowercased catchphrase — a single canonical
        # lookup regardless of a rule's case-sensitivity setting.
        rule_map = {(r.media_id, r.catchphrase.lower()): r for r in rules}
        print(f'Rule map keys: {list(rule_map.keys())}')

        # Step 5: process each comment
        for comment_text, media_id, comment_id, commenter_id in comments:
            print(f'Looking up rule for media_id={media_id}, comment_text={comment_text}')
            rule = rule_map.get((media_id, comment_text.lower()))
            if not rule:
                print(f'No rule found for: media_id={media_id}, text={comment_text}')
                continue

            # Case-sensitive rules need an exact match against the
            # original-case comment text and stored catchphrase.
            if rule.is_case_sensitive and comment_text != rule.catchphrase:
                print(f'Case-sensitive mismatch: got "{comment_text}", expected "{rule.catchphrase}"')
                continue

            if not rule.user.encrypted_instagram_access_token:
                print(f'Skipping {comment_id}: user {rule.user.user_id} has no token')
                continue

            print(f'Sleeping 60s before sending DM for comment {comment_id}')
            await asyncio.sleep(60)

            access_token = decrypt(rule.user.encrypted_instagram_access_token)
            message = random.choice(rule.dm_message)
            print(f'Sending DM for comment {comment_id}, message: {message}')

            sent = await send_dm(rule.user.user_id, comment_id, message, access_token)

            if sent:
                if rule.reply_message:
                    print(f'Sending reply for comment {comment_id}')
                    await send_reply(comment_id, rule.reply_message, access_token)
                db.add(DMLogsModel(
                    commenter_ig_id=commenter_id,
                    media_id=media_id,
                    comment_id=comment_id,
                    rule_id=rule.id
                ))
                rule.count += 1
                await db.commit()
                print(f'Successfully processed comment {comment_id}')
            else:
                print(f'DM failed for comment {comment_id}, skipping')

    except Exception as e:
        print(f'Webhook processing error: {e}')
        await db.rollback()