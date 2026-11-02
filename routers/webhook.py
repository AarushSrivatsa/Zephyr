import hashlib
import hmac
import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from settings import CLIENT_SECRET, VERIFY_TOKEN
from utils.instagram_functions import process_webhook
from utils.logging_config import get_logger

log = get_logger("webhook")

# Fail at startup, not with a 500 on the first webhook.
if not CLIENT_SECRET or not VERIFY_TOKEN:
    raise RuntimeError("CLIENT_SECRET and VERIFY_TOKEN must be set to receive Instagram webhooks")

router = APIRouter(prefix="/instagram", tags=["Instagram"])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
):
    token_ok = hmac.compare_digest(hub_verify_token.encode(), VERIFY_TOKEN.encode())
    if hub_mode == "subscribe" and token_ok:
        log.info("🔗 Webhook endpoint verified by Meta")
        return PlainTextResponse(content=hub_challenge)

    log.warning("🚫 Webhook verification failed (bad mode or verify token)")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(CLIENT_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature.encode(), expected.encode()):
        log.warning("🚫 Rejected webhook — invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        log.warning("⚠️ Rejected webhook — body is not valid JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if data.get("object") != "instagram":
        return {"status": "ignored"}

    background_tasks.add_task(process_webhook, data)
    return {"status": "ok"}