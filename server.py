from fastapi.middleware.cors import CORSMiddleware
from main import app

# No longer required for the bundled frontend (same-origin), but kept in
# case you call this API from another origin (e.g. a mobile app or a
# separately-hosted admin panel). Trim allow_origins to just what you need.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)