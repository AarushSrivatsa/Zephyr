from fastapi import FastAPI
from contextlib import asynccontextmanager
from utils.http_client import client
from routers.payments import router as payments_router
from routers.user import router as authentication_router
from routers.instagram_interaction import router as webhook_router
from routers.rules import router as rules_router
from routers.compliance import router as compliance_router
from utils.background_tasks import scheduler, refresh_instagram_tokens, wipe_deleted_users

router_list = [authentication_router,webhook_router,rules_router,compliance_router,payments_router]

tasklist = [refresh_instagram_tokens]

@asynccontextmanager
async def lifespan(app: FastAPI):
    for task in tasklist:
        scheduler.add_job(refresh_instagram_tokens, 'interval', hours=24)
    scheduler.start()
    yield
    scheduler.shutdown()
    await client.aclose()
    
app = FastAPI(title='Comment2DM Automation',)

for router in router_list:
    app.include_router(router)


