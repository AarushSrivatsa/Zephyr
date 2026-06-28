from fastapi import APIRouter, Query, HTTPException, status, Request, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.initialization import get_db
from database.models import RuleModel, DMLogsModel
from utils.http_client import client
from utils.encryption import decrypt
from settings import VERIFY_TOKEN
from utils.instagram_functions import send_dm,send_reply

router = APIRouter(prefix='/webhook')

@router.get('')
async def verify_webhook(
    hub_mode: str = Query(alias='hub.mode'),
    hub_challenge: int = Query(alias='hub.challenge'),
    hub_verify_token: str = Query(alias='hub.verify_token')
):
    if hub_mode == 'subscribe' and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=str(hub_challenge))
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Verification failed')

@router.post('')
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()

    if data.get('object') != 'instagram':
        return {'status': 'ignored'}

    # Step 1: Collect all comments from payload
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
        return {'status': 'ok'}

    # Step 2: Batch duplicate check
    comment_ids = [c[2] for c in comments]
    existing = await db.execute(
        select(DMLogsModel.comment_id)
        .where(DMLogsModel.comment_id.in_(comment_ids))
    )
    duplicate_ids = {row[0] for row in existing.fetchall()}
    comments = [c for c in comments if c[2] not in duplicate_ids]

    if not comments:
        return {'status': 'ok'}

    # Step 3: Batch rule fetch
    media_ids = [c[1] for c in comments]
    rules_result = await db.execute(
        select(RuleModel)
        .options(selectinload(RuleModel.user))
        .where(
            RuleModel.media_id.in_(media_ids),
            RuleModel.is_active == True
        )
    )
    rules = rules_result.scalars().all()
    rule_map = {(rule.media_id, rule.catchphrase): rule for rule in rules}

    # Step 4: Process each comment
    for comment_text, media_id, comment_id, commenter_id in comments:
        rule = rule_map.get((media_id, comment_text))
        if not rule:
            print(f'No rule found for: {comment_text}')
            continue

        access_token = decrypt(rule.user.encrypted_instagram_access_token)
        await send_dm(rule.user.user_id, comment_id, rule.dm_message, access_token)

        if rule.reply_message:
            await send_reply(comment_id, rule.reply_message, access_token)

        db.add(DMLogsModel(
            commenter_ig_id=commenter_id,
            media_id=media_id,
            comment_id=comment_id,
            rule_id=rule.id
        ))
        rule.count += 1

    return {'status': 'ok'}