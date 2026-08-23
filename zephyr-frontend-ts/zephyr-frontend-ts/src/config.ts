// Zephyr — configuration
//
// Point this at wherever the Zephyr FastAPI backend is deployed. No trailing slash.
export const API_BASE_URL = "http://localhost:8000";
// Where the Instagram OAuth flow should land once the user authorizes the
// app. Must be publicly reachable and MUST match the backend's REDIRECT_URI
// env var exactly. Defaults to this site's own login-callback.html.
export const OAUTH_CALLBACK_URL = `${window.location.origin}/login-callback.html`;
