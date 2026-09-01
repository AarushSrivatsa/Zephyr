// Zephyr — configuration
//
// Frontend is now served by the same FastAPI app (single Render instance),
// so API calls are same-origin — leave this empty rather than hardcoding a host.
export const API_BASE_URL = "";
// Where the Instagram OAuth flow should land once the user authorizes the
// app. Must be publicly reachable and MUST match the backend's REDIRECT_URI
// env var exactly.
export const OAUTH_CALLBACK_URL = `${window.location.origin}/login-callback.html`;

// ---------------------------------------------------------------
// Pricing — ₹399/month for India, $5/month everywhere else.
//
// NOTE: this only controls what text is SHOWN. The actual charge still
// comes from whatever single DODO_PRODUCT_ID the backend's /payments/checkout
// uses (see routers/payments.py) — so this display text isn't truthful yet
// unless/until the backend also picks a product/price by region. Wire that
// up before relying on this for real billing.
//
// India is detected via browser timezone: "Asia/Kolkata" is India's one and
// only IANA timezone, so it's a reasonable client-side signal without a
// geo-IP call. Falls back to the non-India price if detection throws for
// any reason (older browsers, etc).
// ---------------------------------------------------------------
function isLikelyIndia(): boolean {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone === "Asia/Kolkata";
  } catch {
    return false;
  }
}

export const PRICE_DISPLAY = isLikelyIndia() ? "₹399/month" : "$5/month";