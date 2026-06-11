from fastapi import FastAPI
from routers.authentication import router as authentication_router
from contextlib import asynccontextmanager
from utils.http_client import client


router_list = [authentication_router]

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client.aclose()

router_list = [authentication_router]

app = FastAPI(title='Comment2DM Automation',)

for router in router_list:
	app.include_router(router)


