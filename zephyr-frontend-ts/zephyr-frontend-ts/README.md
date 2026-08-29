# Zephyr — HTML + TypeScript + Tailwind CSS frontend

Same app, no bundler. `tsc` emits native ES modules the browser loads
directly via `<script type="module">`, and the Tailwind CLI compiles a
single, minified, purged stylesheet from the utility classes actually used
in the HTML/TS source — no hand-written CSS, no inline `style=` attributes
anywhere in the app.

```
index.html              Landing page (nav, hero, how-it-works, pricing, footer)
login-callback.html     Handles the Instagram OAuth redirect
dashboard.html           Rules / Billing / Account
privacy-policy.html      Privacy policy
data-deletion.html       Self-serve account deletion
css/
  tailwind.css            Tailwind entry point (@tailwind directives only)
  style.css                Compiled output (generated — see Build, below)
src/
  config.ts                API_BASE_URL + OAuth callback URL — edit this first
  types.ts                  Shared interfaces matching the backend's JSON shapes
  api.ts                    Fetch wrapper: token storage, auto-refresh on 401, all endpoints
  ui.ts                     Toasts, HTML-escaping, date formatting, hidden-class helper
  landing.ts                Entry point for index.html
  callback.ts               Entry point for login-callback.html
  dashboard.ts               Entry point for dashboard.html
  delete-account.ts          Entry point for data-deletion.html
js/                        Compiled output (generated — see Build, below)
tailwind.config.js         Design tokens: colors, fonts, shadows, keyframes
tsconfig.json
package.json
```

## 1. Install and build

```bash
npm install
npm run build      # tsc -> js/*.js, tailwindcss -> css/style.css
```

Keep both compiling while you work (two terminals):

```bash
npm run watch:ts
npm run watch:css
```

## 2. Point it at your backend

Edit `src/config.ts`:

```ts
export const API_BASE_URL = "https://your-backend.example.com";
```

Then re-run `npm run build` (or leave the watchers running).

## 3. Serve it

ES modules need to be loaded over `http(s)://`, not opened as a `file://`
path. Any static server works:

```bash
npm run serve       # http-server on http://localhost:5500
# or
python3 -m http.server 5500
```

## 4. Editing styles

There is no hand-written CSS to touch. Everything is Tailwind utility
classes directly on elements in the HTML files (and in the small amount of
markup `dashboard.ts` generates for rule cards, toasts, and form rows).
`tailwind.config.js` holds the design tokens — colors, fonts, shadows,
radii — so a rebrand only touches that one file. `css/tailwind.css` is just
the three `@tailwind` directives plus a couple of true base-layer rules
(font smoothing, the focus ring, reduced-motion) that apply globally and
don't belong on individual elements.

## 5. Backend changes this frontend needs

Add `CORSMiddleware` to `main.py` allowing this frontend's origin (only
needed if you're not serving it same-origin), and point `REDIRECT_URI` /
`payments.py`'s `return_url` at this app's `login-callback.html` /
`dashboard.html`.

## How auth works here

1. "Login with Instagram" sends the browser to `GET {API_BASE_URL}/user/login`.
2. Instagram redirects back to `login-callback.html?code=...`.
3. `callback.ts` calls `GET /user/instagram_callback?code=...`, stores the
   returned tokens in `localStorage`, and redirects to `dashboard.html`.
4. `api.ts` attaches `Authorization: Bearer <access_token>` to every call
   and silently refreshes once via `POST /user/refresh` on a 401.

## Notes on `/rules` and subscriptions

There's no dedicated subscription-status endpoint, so a `403` from `/rules`
is treated as "needs billing" throughout `dashboard.ts`, and
`RuleUpdateRequest`/`RuleCreateRequest` in `types.ts` match the backend's
Pydantic models field-for-field if you want to add a richer status endpoint
later.
