import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, RedirectResponse
from contextlib import asynccontextmanager
from utils.http_client import client
from routers.payments import router as payments_router
from routers.user import router as user_router
from routers.webhook import router as instagram_router
from routers.rules import router as rules_router
from utils.background_tasks import scheduler, refresh_instagram_tokens, wipe_deleted_users
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

router_list = [user_router,instagram_router,rules_router,payments_router]

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(refresh_instagram_tokens,'cron',hour=0,minute=0)
    scheduler.add_job(wipe_deleted_users,'cron',hour=0,minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()
    await client.aclose()
    
app = FastAPI(title='Comment2DM Automation',lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

for router in router_list:
    app.include_router(router)

# ---------------------------------------------------------------
# Frontend (built by the Docker image into /app/frontend)
# ---------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

# Custom static file class that disables caching, so a fresh deploy is
# always picked up immediately instead of the browser/Cloudflare serving
# an old cached js/css bundle.
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.mount("/css", NoCacheStaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", NoCacheStaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

# ---------------------------------------------------------------
# Clean URLs: every canonical page has exactly one clean path.
# Legacy/relative ".html" hits get redirected to the clean path so
# stray links (and browser relative-URL resolution) never 404 and
# ".html" never shows up in the address bar.
# ---------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/index.html", include_in_schema=False)
async def redirect_index_html():
    return RedirectResponse(url="/", status_code=307)

@app.get("/dashboard", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/dashboard.html", include_in_schema=False)
async def redirect_dashboard_html():
    return RedirectResponse(url="/dashboard", status_code=307)

@app.get("/login-callback.html", include_in_schema=False)
@app.get("/callback", include_in_schema=False)
async def serve_login_callback():
    return FileResponse(os.path.join(FRONTEND_DIR, "login-callback.html"))

@app.get("/privacy-policy", include_in_schema=False)
async def serve_privacy_policy():
    return FileResponse(os.path.join(FRONTEND_DIR, "privacy-policy.html"))