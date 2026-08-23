// Zephyr — configuration
//
// Frontend is now served by the same FastAPI app (single Render instance),
// so API calls are same-origin — leave this empty rather than hardcoding a host.
export const API_BASE_URL = "";
// Where the Instagram OAuth flow should land once the user authorizes the
// app. Must be publicly reachable and MUST match the backend's REDIRECT_URI
// env var exactly.
export const OAUTH_CALLBACK_URL = `${window.location.origin}/login-callback.html`;