from utils.http_client import client
from utils.encryption import decrypt
from database.initialization import AsyncSessionLocal
from database.models import RuleModel, DMLogsModel
from sqlalchemy import select, update, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
import random
import asyncio

MIN_DELAY = 60
MAX_DELAY = 120

# comment_ids this process is already handling (guards against duplicate deliveries)
_in_flight: set[str] = set()


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


async def _handle_comment(rule_id: int, media_id: str, comment_id: str, commenter_id: str):
    """Waits with no DB session, re-checks the rule, sends, then opens a new session to save the log."""
    tag = f'[{comment_id}]'
    try:
        # ---- 1. wait: NO database session is open here ----
        delay = random.randint(MIN_DELAY, MAX_DELAY)
        print(f'{tag} No DB session open. Sleeping {delay}s before sending')
        await asyncio.sleep(delay)

        # ---- 2. short session: re-check everything, copy what we need, close ----
        print(f'{tag} Woke up. Opening fresh DB session to re-check rule {rule_id}')
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(RuleModel)
                .options(selectinload(RuleModel.user))
                .where(RuleModel.id == rule_id)
            )
            rule = result.scalar_one_or_none()

            if rule is None:
                print(f'{tag} Rule {rule_id} was deleted while waiting, skipping')
                return
            if not rule.is_active:
                print(f'{tag} Rule {rule_id} was paused while waiting, skipping')
                return
            if not rule.user.encrypted_instagram_access_token:
                print(f'{tag} User {rule.user.user_id} has no token anymore, skipping')
                return

            already = await db.execute(
                select(DMLogsModel.id).where(
                    or_(
                        DMLogsModel.comment_id == comment_id,
                        (DMLogsModel.commenter_ig_id == commenter_id) & (DMLogsModel.rule_id == rule_id)
                    )
                ).limit(1)
            )
            if already.first() is not None:
                print(f'{tag} Already DMed (this comment, or this commenter for this rule), skipping')
                return

            # copy everything needed so we can close the session before any network call
            access_token = decrypt(rule.user.encrypted_instagram_access_token)
            message = random.choice(rule.dm_message)
            reply_text = random.choice(rule.reply_message) if rule.reply_message else None
            ig_user_id = rule.user.user_id
        print(f'{tag} DB session closed. Checks passed')

        # ---- 3. network calls: still no DB session open ----
        print(f'{tag} Sending DM, message: {message}')
        sent = await send_dm(ig_user_id, comment_id, message, access_token)

        if not sent:
            print(f'{tag} DM failed, nothing saved, skipping')
            return

        if reply_text:
            print(f'{tag} Sending public reply')
            await send_reply(comment_id, reply_text, access_token)

        # ---- 4. new short session just to save the sent log ----
        print(f'{tag} Opening new DB session to save sent log')
        async with AsyncSessionLocal() as db:
            db.add(DMLogsModel(
                commenter_ig_id=commenter_id,
                media_id=media_id,
                comment_id=comment_id,
                rule_id=rule_id
            ))
            await db.execute(
                update(RuleModel).where(RuleModel.id == rule_id).values(count=RuleModel.count + 1)
            )
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                print(f'{tag} Log already existed (duplicate task), count not incremented')
                return
        print(f'{tag} Successfully processed, log saved and count incremented')

    except Exception as e:
        print(f'{tag} Error while handling comment: {e}')


async def process_webhook(data: dict):
    ids_in_this_payload: list[str] = []
    try:
        print(f'process_webhook called with object: {data.get("object")}')

        if data.get('object') != 'instagram':
            print('Ignoring non-instagram webhook')
            return

        # Step 1: collect all comments from payload.
        # comment_text keeps its ORIGINAL case, we lower() it wherever needed.
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
                    print('Skipping comment — missing fields')
                    continue
                # skips repeats inside the payload AND ones already waiting from an earlier delivery
                if comment_id in _in_flight:
                    print(f'Skipping {comment_id}: already being handled')
                    continue
                _in_flight.add(comment_id)
                ids_in_this_payload.append(comment_id)
                comments.append((comment_text, media_id, comment_id, commenter_id))

        print(f'Total comments collected (after in-flight dedup): {len(comments)}')
        if not comments:
            print('No comments to process')
            return

        # Step 2: ONE short DB session for the reads, closed before any waiting
        print('Opening DB session for duplicate check and rule lookup')
        async with AsyncSessionLocal() as db:
            existing = await db.execute(
                select(DMLogsModel.comment_id)
                .where(DMLogsModel.comment_id.in_([c[2] for c in comments]))
            )
            duplicate_ids = {row[0] for row in existing.fetchall()}
            print(f'Duplicate comment_ids already in DB: {duplicate_ids}')
            comments = [c for c in comments if c[2] not in duplicate_ids]
            print(f'After DB dedupe: {len(comments)} comments')

            if not comments:
                print('All comments already processed')
                return

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
        print('DB session closed')

        # Always key on the lowercased catchphrase, single canonical lookup
        rule_map = {(r.media_id, r.catchphrase.lower()): r for r in rules}
        print(f'Rule map keys: {list(rule_map.keys())}')

        # Step 3: handle each comment one after another (each waits 60-120s)
        for comment_text, media_id, comment_id, commenter_id in comments:
            print(f'Looking up rule for media_id={media_id}, comment_text={comment_text}')
            rule = rule_map.get((media_id, comment_text.lower()))
            if not rule:
                print(f'No rule found for: media_id={media_id}, text={comment_text}')
                continue

            # Case-sensitive rules need an exact match against the original-case text
            if rule.is_case_sensitive and comment_text != rule.catchphrase:
                print(f'Case-sensitive mismatch: got "{comment_text}", expected "{rule.catchphrase}"')
                continue

            if not rule.user.encrypted_instagram_access_token:
                print(f'Skipping {comment_id}: user {rule.user.user_id} has no token')
                continue

            print(f'Rule {rule.id} matched for comment {comment_id}, handing off')
            await _handle_comment(rule.id, media_id, comment_id, commenter_id)

    except Exception as e:
        print(f'Webhook processing error: {e}')
    finally:
        _in_flight.difference_update(ids_in_this_payload)
        print(f'Released in-flight ids: {ids_in_this_payload}')