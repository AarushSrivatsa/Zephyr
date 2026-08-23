# Zephyr — HTML/CSS + TypeScript frontend

Same app as the plain-JS build, rewritten in TypeScript. No bundler — the
compiler (`tsc`) emits native ES modules that the browser loads directly via
`<script type="module">`. Every file here type-checks with `tsc --strict`.

```
index.html              Landing page
login-callback.html     Handles the Instagram OAuth redirect
dashboard.html          Rules / Billing / Account
css/style.css           Design tokens + all component styles
src/
  config.ts             API_BASE_URL + OAuth callback URL — edit this first
  types.ts               Shared interfaces matching the backend's JSON shapes
  api.ts                  Fetch wrapper: token storage, auto-refresh on 401, all endpoints
  ui.ts                   Toasts, HTML-escaping, date formatting
  landing.ts              Entry point for index.html
  callback.ts             Entry point for login-callback.html
  dashboard.ts             Entry point for dashboard.html
js/                      Compiled output (generated — see Build, below)
tsconfig.json
package.json
```

## 1. Install and build

```bash
npm install
npm run build      # compiles src/*.ts -> js/*.js
```

Keep it compiling while you work:

```bash
npm run watch
```

## 2. Point it at your backend

Edit `src/config.ts`:

```ts
export const API_BASE_URL = "https://your-backend.example.com";
```

Then re-run `npm run build` (or leave `npm run watch` running).

## 3. Serve it

ES modules need to be loaded over `http(s)://`, not opened as a `file://`
path. Any static server works:

```bash
npm run serve       # http-server on http://localhost:5500
# or
python3 -m http.server 5500
```

## 4. Backend changes this frontend needs

Same three items as the plain-JS build — see the notes on CORS,
`REDIRECT_URI`, and the Dodo `return_url` in the earlier handoff. In short:
add `CORSMiddleware` to `main.py` allowing this frontend's origin, and point
`REDIRECT_URI` / `payments.py`'s `return_url` at this app's
`login-callback.html` / `dashboard.html`.

## How auth works here

1. "Connect Instagram" sends the browser to `GET {API_BASE_URL}/user/login`.
2. Instagram redirects back to `login-callback.html?code=...`.
3. `callback.ts` calls `GET /user/instagram_callback?code=...`, stores the
   returned tokens in `localStorage`, and redirects to `dashboard.html`.
4. `api.ts` attaches `Authorization: Bearer <access_token>` to every call
   and silently refreshes once via `POST /user/refresh` on a 401.

## Notes on `/rules` and subscriptions

Same as the plain-JS build: there's no dedicated subscription-status
endpoint, so a `403` from `/rules` is treated as "needs billing" throughout
`dashboard.ts`, and `RuleUpdateRequest`/`RuleCreateRequest` in `types.ts`
match the backend's Pydantic models field-for-field if you want to add a
richer status endpoint later.
