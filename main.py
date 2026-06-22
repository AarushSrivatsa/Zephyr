from fastapi import FastAPI
from contextlib import asynccontextmanager
from utils.http_client import client

from routers.authentication import router as authentication_router
from routers.webhook import router as webhook_router
from routers.rules import router as rules_router

router_list = [authentication_router,webhook_router,rules_router]

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client.aclose()

app = FastAPI(title='Comment2DM Automation',)

for router in router_list:
	app.include_router(router)


