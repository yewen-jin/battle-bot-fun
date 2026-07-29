# battle-bot-fun — Stream B (beats to pixels)

Hackathon build, ~2h window, demo at 21:00. See `PRD.md` for the full spec — this file only covers process, not spec content.

## Ownership

- **Stream B:** `physics.js`, `render.js`, `runner.js`, `index.html`, `preview.html`, `demo.html`.
- **Stream A (partner's, as committed on `data-scrape`):** `beats.js`, `speak.js`, `data/`, `raw/`, `prompts/beats_system.txt`, `1_scrape.py`, `2_merge.py`, `3_embed.py`. An earlier ES-module version of `beats.js`/`speak.js` was built by Claude when the generation layer didn't exist yet (see WORKLOG "Built Stream A's missing piece") — once the partner pushed their own independent versions, the user chose to take the partner's and adapt Stream B's wiring instead (see WORKLOG "Reconciled with partner's independent beats.js/speak.js").

## How beats.js/speak.js are wired into index.html

`beats.js`/`speak.js` are **classic (non-module) scripts**, not ES modules — they set `window.Beats` / `window.Speak`, not named exports. `index.html` loads them in this exact order, before the `type="module"` script: `data/data.js` (sets `window.OOF_DATA`, read synchronously at `beats.js`'s top level) → `beats.js` → `speak.js`. The module script then:
- Shims `window.speak = window.Speak.speak` so `runner.js`'s existing `typeof window.speak === 'function'` check works unchanged.
- Fetches `prompts/beats_system.txt` and `sample_beats.json` into `window.OOF_SYSTEM_PROMPT` / `window.OOF_SAMPLE_BEATS` (both read lazily inside `Beats.generate()`, so this can happen async at page load).
- Populates the bot-picker dropdowns from `window.OOF_DATA.bots` directly (no separate `raw/groups.json` fetch needed).
- Calls `window.Beats.generate(nameA, nameB)` on "Fight!" — it makes one Anthropic call, validates, retries once, and falls back to `window.OOF_SAMPLE_BEATS` on failure. On fallback, `index.html` relabels the fixture's Tombstone/Minotaur captions to whichever bots were actually picked (see WORKLOG for why).

There is **no API-key input field** (removed per explicit user instruction) — `beats.js`'s internal `getApiKey()` calls the browser's `prompt()` on first use and caches the key in `localStorage` (key `oof_api_key`) from then on.

`beats.js` calls the Anthropic API **directly from the browser** (no backend) — the key is visible to anyone with dev tools open on the page. Acceptable for a local demo, not for any public deployment.

## Body-state shape (contract between physics.js and render.js)

Fixed before either file is written. Do not change without updating both.

```js
// one object per bot, created by physics.js's createBody(x, y, color), read (not mutated) by render.js
{
  x, y,            // position, world units, 160x90 arena, +y down
  vx, vy,          // velocity, units/sec
  angle,           // radians, current rotation
  av,              // angular velocity, rad/s
  scaleX, scaleY,  // squash/stretch multipliers, default 1, written every tick by physics.js's step() — render.js just reads and applies them
  squash,          // internal to physics.js: current squash magnitude (0 = normal), decays every tick — render.js should not read this, only scaleX/scaleY
  squashAxis,      // internal to physics.js: 'y' (floor-contact squash, compress vertical/stretch horizontal) or 'x' (wall-contact, compress horizontal/stretch vertical)
  color,           // hex string, one of CONFIG.palette, assigned at creation to distinguish bot a/b
  eyes,            // [eye, eye] — two independent spring-mass pupils, see below
}

// one eye, owned/evolved by physics.js's step(), drawn (not mutated) by render.js
{
  ex, ey,          // pupil offset from socket center, in the body's own rotated frame, world units
  evx, evy,        // pupil offset velocity, units/sec
}
```

**Eyes:** each tick, `physics.js` derives this body's acceleration since the last tick (from the velocity delta — captures gravity, bounces, and any `applyImpulse()` calls since the last `step()`), rotates it into the body's own frame, and runs each eye through a damped spring pulling back to `(0,0)` with a forcing term proportional to `-acceleration`. Offset is clamped to `CONFIG.eyeClampRadius`. `render.js` draws each eye's socket at a fixed local offset (`CONFIG.eyeOffsetX/Y`, mirrored left/right) and the pupil at `socket + (ex, ey)` — both inside the same rotated/scaled transform as the body, so eyes automatically follow rotation and (once stage 4 lands) squash/stretch.

**Optional sprite fields** (not part of `createBody`'s return — set by whoever assembles bodies, e.g. `preview.html`/`runner.js`, as plain property assignment after creation; `physics.js` never reads or writes these):

```js
body.name    // bot's real name, e.g. "Tombstone" — used as the sprite lookup key
body.sprite  // HTMLImageElement | null | undefined — if set and truthy, render.js draws it
             // instead of the colored blob (still rotated/squashed/pixel-snapped the same way)
```

`render.js` exports `loadSprite(name)` which fetches `./media/bots/<slugified-name>.png` and resolves to the image, or `null` if it 404s/errors — so bots without art fall back to the blob automatically. Drop PNGs into `media/bots/` (naming convention in `media/bots/README.md`) at any point, per bot, with zero code changes.

## CONFIG (single mutable object, owned by physics.js — everyone else only reads it)

`physics.js` exports `CONFIG`. `render.js` (and later runner.js) import it and read from it — never hardcode world dimensions, bot radius, rotation step, or palette locally, and never write to it. This is the exact starting shape both files are built against:

```js
export const CONFIG = {
  worldW: 160,
  worldH: 90,
  floorY: 78,
  wallLeft: 8,
  wallRight: 152,
  gravity: 420,
  floorRestitution: 0.55,
  wallRestitution: 0.60,
  groundDampingLinear: 0.82,
  groundDampingAngular: 0.70,
  botRadius: 7,
  rotationQuantizeDeg: 15,
  pixelScale: 8,
  palette: ['#1a1a2e', '#e94560', '#0f3460', '#16213e', '#f5f5f5', '#ffd460', '#533483', '#0a0a0a'],
  outlineColor: '#0a0a0a',
  shadowColor: 'rgba(0,0,0,0.35)',
}
```

## WORKLOG.md

Append-only log of decisions, one entry per merge/checkpoint or notable call. Never delete entries; a reverted decision gets `Status: reverted`, not removal. Template:

```markdown
## [T+<minutes>] Title

**Status:** completed | in-progress | blocked | reverted

**Summary:** one or two sentences.

**Decisions & Reasoning:**
- Decision: ...
  Why: ...

**Files Changed:** ...

**Backtrack Notes:** how to undo this, if needed.
```

## What I cannot verify without the user looking

Visual output (does it read as funny, do the googly eyes land, does the squash/stretch feel right, does pixel snapping look clean at 8x), audio/caption timing feel, and whether the demo is actually fun to watch. Do not claim these work — report what was built and ask the user to check it in the browser.

## Constraints carried over from the PRD (most likely to be violated)

- **Launch method (revised from PRD):** plain ES modules don't load over `file://` in Chrome/Safari (CORS-style restriction), so double-clicking `index.html`/`preview.html` gets stuck on nothing rendering. Actual launch is `python3 devserver.py` from the project root (not bare `python3 -m http.server` — see below), then open `http://localhost:8000/...`. Still no build step, no bundler, no `npm install` — just needs one terminal command running during the demo. See WORKLOG entry "`preview.html` stuck on 'loading…'".
- **Use `devserver.py`, not bare `python3 -m http.server`:** the stdlib server sends no `Cache-Control` header, which lets browsers heuristically cache JS/images across ordinary reloads — edits can silently fail to show up without a hard refresh. `devserver.py` is a ~15-line wrapper that adds `Cache-Control: no-store` to every response. See WORKLOG entry "browser cache issue" for how this was diagnosed (and why query-string cache-busting on import paths was tried and reverted — it risks loading two separate module instances of the same file if not every cross-reference is kept in sync).
- Fixed timestep 1/60s, accumulator clamped to 0.25s. Never variable `dt`.
- 160×90 offscreen canvas, 8× upscale, `imageSmoothingEnabled = false`. Build this in from line one — do not pixelate a smooth renderer later.
- World units, impulse scale, and beat schema (Section 2 of PRD) are immutable. If beats don't fit, that's a Stream A/prompt bug, not a reason to change physics constants.
- All tunables live in `physics.js`'s single mutable `CONFIG` object. Nobody else writes to it in parallel.
