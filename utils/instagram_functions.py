"""
Comment -> DM automation.

Flow for every webhook delivery:

  1. process_webhook   pulls comments out of the payload, drops duplicates,
                       and opens ONE short DB session to find matching rules.
                       Session is closed before anything slow happens.
  2. _handle_comment   (one task per matched comment, run in parallel)
                       sleeps 60-120s with NO db session open, then takes a
                       per-owner lock.
  3. _prepare_send     inside the lock: a NEW short DB session re-checks the
                       rule / subscription / duplicates, copies out plain
                       values, and closes.
  4. send_dm / send_reply   network calls, still no DB session open.
  5. _save_log         another NEW short session, only to write the log row
                       and bump the rule's counter.

Concurrency model:
  * different account owners  -> fully parallel
  * same account owner        -> the check -> send -> log section is serialized
                                 by a lock keyed on owner id, so two tasks can
                                 never both see "not DMed yet" and both send.
"""
import asyncio
import random
import weakref
from collections import defaultdict
from datetime import datetime, timezone
from typing import NamedTuple

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from database.initialization import AsyncSessionLocal
from database.models import DMLogsModel, RuleModel, UserModel
from utils.encryption import decrypt
from utils.http_client import client
from utils.logging_config import get_logger

log = get_logger("dm")

MIN_DELAY = 60
MAX_DELAY = 120
HTTP_TIMEOUT = 15.0
GRAPH_URL = "https://graph.instagram.com/v25.0"

# comment_ids this process is already handling (guards against duplicate deliveries)
_in_flight: set[str] = set()

# One lock per account owner. Weak values: a lock disappears on its own once
# nobody is holding or waiting on it, so this dict never grows forever.
_owner_locks: "weakref.WeakValueDictionary[str, asyncio.Lock]" = weakref.WeakValueDictionary()


# ----------------------------------------------------------------------------
# small data holders (plain values only, safe to use after a session is closed)
# ----------------------------------------------------------------------------
class _Comment(NamedTuple):
    text: str
    media_id: str
    comment_id: str
    commenter_id: str
    commenter_name: str  # "@bob", or the raw id if Instagram didn't send a username


class _Job(NamedTuple):
    comment: _Comment
    rule_id: int
    owner_id: str
    owner_name: str  # "@shop"


class _ReadyToSend(NamedTuple):
    ig_user_id: str
    access_token: str
    dm_text: str
    reply_text: str | None


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def _owner_lock(owner_id: str) -> asyncio.Lock:
    lock = _owner_locks.get(owner_id)
    if lock is None:
        lock = asyncio.Lock()
        _owner_locks[owner_id] = lock
    return lock


def _matches(rule: RuleModel, text: str) -> bool:
    if rule.is_case_sensitive:
        return text == rule.catchphrase
    return text.casefold() == rule.catchphrase.casefold()


def _owner_block_reason(owner: UserModel) -> str | None:
    """Why this owner's rules must not fire right now (None = all good)."""
    if owner.deleted_at is not None:
        return "account was deleted"
    if not owner.encrypted_instagram_access_token:
        return "no Instagram token connected"
    sub = owner.subscription
    if sub is None:
        return "no subscription"
    billing = sub.next_billing_date
    if billing.tzinfo is None:
        billing = billing.replace(tzinfo=timezone.utc)
    if billing < datetime.now(timezone.utc):
        return "subscription lapsed"
    return None


# ----------------------------------------------------------------------------
# Instagram API calls (no DB session is ever open while these run)
# ----------------------------------------------------------------------------
async def send_dm(ig_user_id: str, comment_id: str, message: str, access_token: str, who: str) -> bool:
    try:
        response = await client.post(
            f"{GRAPH_URL}/{ig_user_id}/messages",
            json={"recipient": {"comment_id": comment_id}, "message": {"text": message}},
            params={"access_token": access_token},
            timeout=HTTP_TIMEOUT,
        )
    except Exception as e:
        # only the exception type: httpx messages can echo the URL (which carries the token)
        log.error("❌ DM to %s failed — network error (%s)", who, type(e).__name__)
        return False

    if response.status_code != 200:
        log.error("❌ DM to %s failed — HTTP %s: %s", who, response.status_code, response.text[:300])
        return False
    return True


async def send_reply(comment_id: str, message: str, access_token: str, who: str) -> bool:
    try:
        response = await client.post(
            f"{GRAPH_URL}/{comment_id}/replies",
            params={"message": message, "access_token": access_token},
            timeout=HTTP_TIMEOUT,
        )
    except Exception as e:
        log.warning("⚠️ Public reply to %s failed — network error (%s)", who, type(e).__name__)
        return False

    if response.status_code != 200:
        log.warning("⚠️ Public reply to %s failed — HTTP %s: %s", who, response.status_code, response.text[:300])
        return False
    return True


# ----------------------------------------------------------------------------
# per-comment pipeline
# ----------------------------------------------------------------------------
async def _prepare_send(job: _Job) -> _ReadyToSend | None:
    """Fresh short DB session: re-check everything after the sleep, copy out what we need, close."""
    c = job.comment
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RuleModel)
            .options(selectinload(RuleModel.user).selectinload(UserModel.subscription))
            .where(RuleModel.id == job.rule_id)
        )
        rule = result.scalar_one_or_none()

        if rule is None:
            log.info("🗑️ Skipped %s — rule #%s was deleted while waiting", c.commenter_name, job.rule_id)
            return None
        if not rule.is_active:
            log.info("⏸️ Skipped %s — rule #%s was paused while waiting", c.commenter_name, rule.id)
            return None
        if rule.media_id != c.media_id or not _matches(rule, c.text):
            log.info("✏️ Skipped %s — rule #%s was edited while waiting and no longer matches", c.commenter_name, rule.id)
            return None

        reason = _owner_block_reason(rule.user)
        if reason:
            log.warning("🚫 Skipped %s — %s: %s", c.commenter_name, job.owner_name, reason)
            return None

        if not rule.dm_message:
            log.error("❌ Skipped %s — rule #%s has no DM message", c.commenter_name, rule.id)
            return None

        already = await db.execute(
            select(DMLogsModel.id)
            .where(
                or_(
                    DMLogsModel.comment_id == c.comment_id,
                    and_(DMLogsModel.commenter_ig_id == c.commenter_id, DMLogsModel.rule_id == rule.id),
                )
            )
            .limit(1)
        )
        if already.first() is not None:
            log.info("⏭️ Skipped %s — already DMed for rule #%s", c.commenter_name, rule.id)
            return None

        ready = _ReadyToSend(
            ig_user_id=rule.user.user_id,
            access_token=decrypt(rule.user.encrypted_instagram_access_token),
            dm_text=random.choice(rule.dm_message),
            reply_text=random.choice(rule.reply_message) if rule.reply_message else None,
        )
    # session is closed here
    return ready


async def _save_log(job: _Job) -> None:
    """Fresh short DB session, only to record the DM and bump the counter."""
    c = job.comment
    async with AsyncSessionLocal() as db:
        try:
            db.add(
                DMLogsModel(
                    commenter_ig_id=c.commenter_id,
                    media_id=c.media_id,
                    comment_id=c.comment_id,
                    rule_id=job.rule_id,
                )
            )
            await db.flush()  # duplicate-key errors surface HERE, inside the try
            await db.execute(
                update(RuleModel).where(RuleModel.id == job.rule_id).values(count=RuleModel.count + 1)
            )
            await db.commit()
            log.debug("📝 Log saved for %s (rule #%s)", c.commenter_name, job.rule_id)
        except IntegrityError:
            await db.rollback()
            log.warning("⚠️ Log for %s already existed (rule #%s) — counter not incremented", c.commenter_name, job.rule_id)
        except Exception:
            await db.rollback()
            log.exception(
                "🚨 DM to %s WAS SENT but saving its log failed — a duplicate DM is possible",
                c.commenter_name,
            )


async def _send_for_comment(job: _Job) -> None:
    c = job.comment

    ready = await _prepare_send(job)  # opens + closes its own session
    if ready is None:
        return

    sent = await send_dm(ready.ig_user_id, c.comment_id, ready.dm_text, ready.access_token, c.commenter_name)
    if not sent:
        return
    log.info("✅ DM sent → %s  (rule #%s, owner %s)", c.commenter_name, job.rule_id, job.owner_name)

    if ready.reply_text and await send_reply(c.comment_id, ready.reply_text, ready.access_token, c.commenter_name):
        log.info("💬 Public reply sent → %s  (rule #%s, owner %s)", c.commenter_name, job.rule_id, job.owner_name)

    await _save_log(job)  # opens + closes its own session


async def _handle_comment(job: _Job) -> None:
    c = job.comment
    try:
        delay = random.randint(MIN_DELAY, MAX_DELAY)
        log.info(
            '⏳ %s commented "%s" → rule #%s (%s). DM queued, sending in %ss',
            c.commenter_name, c.text, job.rule_id, job.owner_name, delay,
        )
        await asyncio.sleep(delay)  # NO database session is open during the wait

        # Same owner: one at a time (check -> send -> log). Different owners: parallel.
        async with _owner_lock(job.owner_id):
            await _send_for_comment(job)

    except asyncio.CancelledError:
        log.warning("🛑 Shutting down — pending DM to %s (rule #%s) was dropped", c.commenter_name, job.rule_id)
        raise
    except Exception:
        log.exception("💥 Unexpected error handling comment %s from %s", c.comment_id, c.commenter_name)


# ----------------------------------------------------------------------------
# webhook entry point
# ----------------------------------------------------------------------------
def _extract_comments(data: dict, claimed: list[str]) -> list[_Comment]:
    comments: list[_Comment] = []
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            value = change.get("value") or {}
            sender = value.get("from") or {}
            text = (value.get("text") or "").strip()
            media_id = (value.get("media") or {}).get("id")
            comment_id = value.get("id")
            commenter_id = sender.get("id")

            if not all([text, media_id, comment_id, commenter_id]):
                log.debug("Ignoring comment event with missing fields")
                continue
            if comment_id in _in_flight:
                log.debug("Ignoring comment %s — already being handled", comment_id)
                continue

            _in_flight.add(comment_id)
            claimed.append(comment_id)
            username = sender.get("username")
            comments.append(
                _Comment(text, media_id, comment_id, commenter_id, f"@{username}" if username else str(commenter_id))
            )
    return comments


async def _plan_jobs(comments: list[_Comment]) -> list[_Job]:
    """ONE short DB session: drop already-handled comments, load rules, then close before returning."""
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(DMLogsModel.comment_id).where(DMLogsModel.comment_id.in_([c.comment_id for c in comments]))
        )
        done = {row[0] for row in existing.fetchall()}
        comments = [c for c in comments if c.comment_id not in done]
        if not comments:
            return []

        rules_result = await db.execute(
            select(RuleModel)
            .options(selectinload(RuleModel.user).selectinload(UserModel.subscription))
            .where(
                RuleModel.media_id.in_({c.media_id for c in comments}),
                RuleModel.is_active.is_(True),
            )
        )
        rules = rules_result.scalars().all()
    # session is closed here — everything below is plain Python

    # Several rules can share a post (e.g. "GUIDE" case-sensitive AND "guide").
    # Case-sensitive rules go first so the most specific rule wins.
    rules_by_media: dict[str, list[RuleModel]] = defaultdict(list)
    for r in sorted(rules, key=lambda r: not r.is_case_sensitive):
        rules_by_media[r.media_id].append(r)

    jobs: list[_Job] = []
    for c in comments:
        rule = next((r for r in rules_by_media.get(c.media_id, []) if _matches(r, c.text)), None)
        if rule is None:
            log.debug('No rule for "%s" on media %s', c.text, c.media_id)
            continue

        owner = rule.user
        if c.commenter_id == owner.user_id:
            log.debug("Ignoring %s — that's the account owner's own comment", c.commenter_name)
            continue

        reason = _owner_block_reason(owner)
        if reason:
            log.warning("🚫 Skipped %s — @%s: %s", c.commenter_name, owner.username, reason)
            continue

        jobs.append(_Job(c, rule.id, owner.user_id, f"@{owner.username}"))
    return jobs


async def process_webhook(data: dict) -> None:
    claimed: list[str] = []
    try:
        if data.get("object") != "instagram":
            return

        comments = _extract_comments(data, claimed)
        if not comments:
            return

        jobs = await _plan_jobs(comments)
        if not jobs:
            return

        log.info("📥 %s comment(s) matched a rule", len(jobs))
        # Every job runs concurrently; jobs for the same owner queue up on that owner's lock.
        await asyncio.gather(*(_handle_comment(job) for job in jobs), return_exceptions=True)

    except Exception:
        log.exception("💥 Webhook processing crashed")
    finally:
        _in_flight.difference_update(claimed)