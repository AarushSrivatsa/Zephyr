# /assets

Drop the real brand files here with these exact names and every page picks
them up automatically — no code changes needed:

| File                 | Used for                                              | Suggested size |
|----------------------|--------------------------------------------------------|-----------------|
| `instagram-logo.png` | Icon inside every "Login with Instagram" button        | 48×48, transparent |
| `zephyr-logo.png`    | Logo mark next to the wordmark in the nav/rail          | 64×64, transparent |
| `zephyr-font.png`    | Logo wordmark (the stylized "Zephyr" text as an image)  | ~200×48, transparent |

Until a file exists, that spot falls back to the built-in placeholder (a
generic Instagram glyph, the wave mark, or plain "Zephyr" text) — see
`ts/asset-fallback.ts`. Nothing breaks either way; this is purely additive.
