from fastapi import FastAPI
from routers.authentication import router as authentication_router

router_list = [authentication_router]

app = FastAPI(title='Comment2DM Automation')

for router in router_list:
	app.include_router(router)


