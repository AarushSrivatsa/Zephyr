from fastapi import FastAPI
from contextlib import asynccontextmanager
from utils.http_client import client
from routers.payments import router as payments_router
from routers.user import router as user_router
from routers.instagram.main_router import router as instagram_router
from routers.rules import router as rules_router
from utils.background_tasks import scheduler, refresh_instagram_tokens, wipe_deleted_users, publish_scheduled_posts
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

router_list = [user_router,instagram_router,rules_router,payments_router]
tasklist = [refresh_instagram_tokens, wipe_deleted_users]

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(refresh_instagram_tokens,'cron',hour=0,minute=0)
    scheduler.add_job(wipe_deleted_users,'cron',hour=0,minute=0)
    scheduler.add_job(publish_scheduled_posts, 'interval',minutes=2)
    scheduler.start()
    yield
    scheduler.shutdown()
    await client.aclose()
    
app = FastAPI(title='Comment2DM Automation',lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

for router in router_list:
    app.include_router(router)


