# WORKLOG

Append-only. See `CLAUDE.md` for the entry template and process.

## [T+0] Read PRD, committed sample_beats.json

**Status:** completed

**Summary:** Read `PRD.md` in full. Hand-authored `sample_beats.json` — 20-beat Tombstone vs. Minotaur fight, winner "a" by KO — validated against the schema in PRD Section 2 (ascending `t`, gaps ≥0.8s, magnitude/spin/shake bands per severity, final beat massive on the loser with shake 1.0). User reviewed and approved.

**Decisions & Reasoning:**
- Decision: kept `fact` fields to safe, mechanism-level claims (Tombstone = full-body spinner, Minotaur = hydraulic self-righting forks) rather than specific win/season counts.
  Why: not confident of exact historical records; Stream A's real generator pulls actual scraped stats, this file only needed to be schema-valid and demo-able.
- Decision: spread beats across ~37s (not tightly packed at the low end of the 30–45s range).
  Why: gives room for the glancing → solid → massive escalation the PRD asks for in Section 7 (tuning) without rushing the ending.

**Files Changed:** `sample_beats.json` (created)

**Backtrack Notes:** Frozen dev fixture per PRD Section 2 — should not need reverting; if it does, no downstream files depend on it yet.

## [T+~5] Set up CLAUDE.md + WORKLOG.md, fixed body-state shape

**Status:** completed

**Summary:** Added `CLAUDE.md` covering Stream B ownership boundaries, the WORKLOG convention, the "cannot verify" list, and carried-over PRD constraints. Fixed the per-bot body-state shape (`{x, y, vx, vy, angle, av, scaleX, scaleY}`) as the contract between `physics.js` and `render.js` before fanning out work on either file.

**Decisions & Reasoning:**
- Decision: minimal process setup (CLAUDE.md + WORKLOG.md), not the full role-table/agent-definition scaffolding from the subagent-orchestration skill.
  Why: 2-hour build window — full scaffolding overhead isn't worth it for a one-night project; user confirmed this scope directly.
- Decision: `scaleX`/`scaleY` included in the body shape now even though squash/stretch (stage 4) hasn't been built yet.
  Why: avoids a second contract change later — render.js can read-and-apply them from the start (no-op at 1/1) so wiring doesn't need to change when physics.js starts writing real values.

**Files Changed:** `CLAUDE.md` (created), `WORKLOG.md` (created)

**Backtrack Notes:** If the body-state shape needs to change, both `physics.js` and `render.js` briefs/implementations must be updated together — check this file's next entry for what each subagent actually built before changing the shape.

## [T+~10] physics.js + render.js built in parallel, wired preview.html

**Status:** completed

**Summary:** Dispatched two subagents concurrently against the fixed `CONFIG`/body-state contract in `CLAUDE.md` — one for `physics.js`, one for `render.js`. Both landed clean, matched the contract exactly (no field-name drift), and passed a manual read + `node --check`. Wrote `preview.html` (not the final `index.html`) with hardcoded impulses lifted from `sample_beats.json` to eyeball the integrator + renderer together in a browser before building eyes/squash/runner.

**Decisions & Reasoning:**
- Decision: `physics.js`'s `step(bodies, dt)` is a pure per-call integrator with no internal accumulator/RAF loop, even though PRD Section 4 prose describes the accumulator under Stream B's general scope.
  Why: the accumulator/clock is runner.js's job (not built yet) — keeping `step()` pure makes it callable from both the temporary `preview.html` harness now and the real runner later without changing physics.js.
- Decision: built `preview.html` instead of starting `index.html` early.
  Why: PRD's merge protocol says `index.html` is a thin shell touched only during merge, agreed once at T+5. A throwaway preview file avoids pre-committing to shell structure before eyes/squash/runner exist.
- Decision: `preview.html` hardcodes 5 impulses copied from `sample_beats.json` rather than fetching the JSON file.
  Why: `fetch()` of a local file under `file://` (double-click, no server) is unreliable across browsers — this is a real risk for the eventual `index.html` too. Deferred solving it properly to the runner.js stage, since that's where beat-file loading actually needs to work; flagging it now so it isn't a surprise at T+40 merge.

**Files Changed:** `physics.js` (created), `render.js` (created), `preview.html` (created), `WORKLOG.md`, task list updated

**Backtrack Notes:** If `physics.js`/`render.js` need rework, `preview.html` isolates the regression easily (no eyes/squash/runner in the loop yet). The `file://` fetch risk for loading `sample_beats.json` in the real `index.html` is unresolved — needs a decision before stage 5/6 (inline the JSON as a `<script type="application/json">` block, or confirm fetch actually works in the browser being used for the demo).

## [T+~12] `preview.html` stuck on "loading…" — file:// blocks ES module imports

**Status:** completed

**Summary:** Opening `preview.html` via double-click (`file://`) left the page stuck on "loading…" — Chrome/Safari block `<script type="module">` imports over `file://` (CORS-style restriction on modules, separate from the earlier-flagged `fetch()`-of-JSON risk). User chose to run a local static server instead of switching demo browsers.

**Decisions & Reasoning:**
- Decision: run `python3 -m http.server 8000` from the project root for dev and demo; open `http://localhost:8000/...` instead of double-clicking the HTML file.
  Why: user's choice between (a) demo in Firefox only (which allows file:// module imports) or (b) a one-line local server. Chose the server — more robust across whatever browser is actually used at demo time, at the cost of needing one terminal command running.
  Alternatives considered: Firefox-only demo (rejected — too fragile if the demo machine/browser isn't guaranteed); converting away from ES modules to classic scripts (not considered seriously — would violate the PRD's explicit "plain ES modules" constraint and is a bigger rewrite for a 2h build).

**Files Changed:** none (infra/process decision, no code changed)

**Backtrack Notes:** If a server turns out to be unavailable at demo time (no Python, no terminal access), fall back to opening in Firefox — `preview.html`/`index.html` code doesn't need to change either way, only how it's launched.

## [T+~15] Sprite-swap hook added to render.js, blobs stay the default

**Status:** completed

**Summary:** User wants to hand-produce sprite art for all 24 Pro League bots in the background, to swap in later if time allows. Rather than building a full sprite system now, added a minimal optional hook to `render.js`: `loadSprite(name)` resolves `./media/bots/<slug>.png` to an `Image` or `null`; `drawBody()` draws `body.sprite` in place of the blob if it's truthy, otherwise the exact same blob path as before runs unchanged. `preview.html` now sets `body.name` and calls `loadSprite()` for both bots, proving the fallback works today (no art exists yet, so both still render as blobs).

**Decisions & Reasoning:**
- Decision: did not build the 24-bot sprite system now; flagged that the PRD (Section 8) explicitly lists "hand-drawn sprite sheets" as out of scope and that the blob aesthetic is load-bearing for the joke (Section 1).
  Why: user's call to make after hearing the tradeoff — chose to keep building with blobs now and hold the door open, not to block on art that may not finish in time.
  Alternatives considered: full 24-bot media folder + selector now (rejected by user — too much time risk before 21:00); Firefox-only / no hook at all (rejected — user explicitly wants the swap-in path kept open).
- Decision: `name`/`sprite` are plain properties bolted onto the body object by the caller, not part of `createBody()`'s contract in `physics.js`.
  Why: keeps `physics.js` untouched and re-verification-free; `physics.js` never reads these fields so there's no coupling risk.

**Files Changed:** `render.js` (added `loadSprite`, sprite branch in `drawBody`), `preview.html` (wires name + sprite loading), `media/bots/README.md` (created — naming convention), `CLAUDE.md` (documented optional sprite fields)

**Backtrack Notes:** Fully backward compatible — if `body.sprite` is never set, rendering is byte-for-byte the same blob path verified earlier. To fully revert, delete the `if (body.sprite)` branch and the `loadSprite`/`slugify` functions from `render.js`; nothing else depends on them yet.

## [T+~20] Googly eyes — spring-mass pupils

**Status:** completed

**Summary:** Added two independent spring-mass pupils per body. `physics.js` derives per-tick acceleration from the velocity delta since the last `step()` call (this single measurement naturally captures gravity, floor/wall bounces, and any impulses applied in between — no separate signal needed for each), rotates it into the body's own frame, and runs each eye's `(ex, ey, evx, evy)` through a damped spring pulling toward `(0,0)` with a forcing term proportional to `-acceleration`, clamped to `CONFIG.eyeClampRadius`. `render.js` draws sockets at a fixed local offset and pupils at `socket + (ex, ey)`, inside the same rotate/scale transform as the body — so eyes inherit rotation and (later) squash/stretch for free, same pattern as the sprite hook.

**Decisions & Reasoning:**
- Decision: measure acceleration as `(vx,vy)` delta across a single `step()` call, comparing to `vx/vy` read at the top of `stepBody` (before this tick's gravity/collision), rather than tracking a separate `prevVx`/`prevVy` field across calls.
  Why: since `applyImpulse()` mutates `vx`/`vy` directly before `step()` runs, reading `body.vx` at function entry already reflects any impulse since the last tick — one clean measurement covers impulse + this tick's own gravity/bounce, with no extra state needed.
- Decision: transform world-frame acceleration into the body's own rotated frame before driving the spring (using the body's actual continuous `angle`, not the render-quantized one), rather than keeping pupil offsets world-aligned.
  Why: render.js already draws inside a `translate + rotate(quantized) + scale` block — keeping the eye math in the same local frame means sockets/pupils just plug into that existing transform with no extra unrotate step at draw time. Tradeoff: pupils will swing somewhat with the body's own spin, not purely with world-frame linear acceleration — accepted as good-enough for a comedic prop, not a physically rigorous simulation.
  Alternatives considered: world-aligned pupil offsets with an explicit unrotate at draw time — more "correct" inertial behavior but adds complexity for a difference likely invisible at 12fps/15°-quantized render.
- Decision: `CONFIG` gained 8 new eye-related fields (`eyeStiffness`, `eyeDamping`, `eyeAccelGain`, `eyeClampRadius`, `eyeSocketRadius`, `pupilRadius`, `eyeOffsetX/Y`) — un-tuned starting guesses, not yet eyeballed against the sample fight.
  Why: PRD Section 4/7 explicitly asks for stiffness/damping to be exposed as tunables; picked plausible starting values so the mechanism is provably wired before the tuning pass (T+55 per PRD timeline) dials them in.

**Files Changed:** `physics.js` (CONFIG additions, `createEye`/`updateEye`, `stepBody` now derives per-tick acceleration and updates eyes), `render.js` (`drawEyes`, called from `drawBody`), `CLAUDE.md` (documented eye shape + eye field additions to CONFIG)

**Backtrack Notes:** To revert, remove the 8 `eye*`/`pupilRadius` CONFIG keys, `createEye`, the eye-update block in `stepBody`, `eyes` from `createBody`'s return, and `drawEyes` + its call site in `render.js`. Nothing else in the codebase reads `body.eyes` yet (runner.js/index.html don't exist).

## [T+~25] Squash and stretch on impact

**Status:** completed

**Summary:** `physics.js`-only change — no `render.js` edits needed since it already reads/applies `scaleX`/`scaleY` unconditionally (wired during the sprite-hook work). On floor or wall contact, `stepBody` now records the incoming impact speed (`|vy|` for floor, `|vx|` for wall), sets `body.squash = min(squashCoefficient * impactSpeed, squashMax)` and `body.squashAxis` to `'y'` or `'x'`, then every tick decays `squash` by `exp(-squashDecayRate * dt)` and derives `scaleX`/`scaleY` from it (compress the contact axis, stretch the other, `scaleOther = 1/scaleContact`).

**Decisions & Reasoning:**
- Decision: squash is a single scalar + an axis flag (`'y'` or `'x'`), overwritten (not accumulated/maxed) on each new contact.
  Why: simpler than tracking independent X/Y squash amounts that could both be nonzero at once (which would break the `scaleOther = 1/scaleAxis` volume-conserving formula) — a corner hit overwriting a floor hit's residual squash is imperceptible in practice.
- Decision: extended the PRD's literal formula (`scaleY = 1 - k·impact, scaleX = 1/scaleY`, written for floor contact) symmetrically to wall contact (`scaleX = 1 - k·impact, scaleY = 1/scaleX`), rather than always squashing vertically regardless of contact direction.
  Why: reads better — squash happens along the actual axis of impact — and is a direct, narrow extension of the given formula, not a new mechanic.
- Decision: `squashDecayRate: 12` (exponential decay, ~5% of initial squash remaining after 0.25s) and `squashCoefficient: 0.0025` / `squashMax: 0.6` are un-tuned starting guesses picked to keep scaleY/scaleX in a sane 0.4–1.0 range across the impulse table's speed range (50–200 u/s plus fall speeds).
  Why: same reasoning as the eye constants — provably wired now, real tuning happens in the T+55 pass with live sliders.

**Files Changed:** `physics.js` (CONFIG additions, contact blocks now record impact speed + squash, squash decay/apply block in `stepBody`, `squash`/`squashAxis` added to `createBody`'s return), `CLAUDE.md` (documented squash/squashAxis as physics.js-internal, not part of what render.js should read)

**Backtrack Notes:** To revert, remove `squashCoefficient`/`squashMax`/`squashDecayRate` from `CONFIG`, the `squash`/`squashAxis` fields from `createBody`, and the impact-speed-capture + squash-decay/apply blocks from `stepBody`. `render.js` needs no changes either way — reverting just means `scaleX`/`scaleY` stay `1` forever again, same as before this entry.

## [T+~30] preview.html gap fix (real sample_beats.json) + runner.js built

**Status:** completed

**Summary:** User reported "not smooth" in preview.html; turned out to be the preview's 5-hardcoded-impulse test schedule leaving long idle gaps, not a physics/render bug. Fixed by having `preview.html` `fetch('./sample_beats.json')` and play all 20 real beats — this also confirmed `fetch()` of a local JSON file works fine now that we're served over `localhost` (resolves the file:// risk flagged earlier). Then built `runner.js`: walks a beat array against the same fixed-timestep/throttled-render pattern preview.html had been using inline, firing impulses at `beat.t`, calling `speak(line)` (no-op-safe if `window.speak` doesn't exist), updating a caption element, and applying camera shake as a CSS transform on the visible canvas. Refactored `preview.html` to call `runFight()` instead of duplicating the loop.

**Decisions & Reasoning:**
- Decision: `speak(beat.line)` and the caption update fire at `beat.t - CONFIG.speakLeadSeconds` (0.15s), while the impulse fires at exactly `beat.t`.
  Why: PRD's merge protocol (Section 6, step 3) explicitly anticipates TTS lag and prescribes firing speak ~150ms early so voice and impact perceptually coincide — built this in now since it's cheap, rather than waiting to discover the same lag during the T+40 merge.
  Alternatives considered: fire speak/caption and impulse at the same instant — rejected per the PRD's explicit guidance that this reads as commentary lagging the hit.
- Decision: camera shake is a CSS `transform: translate()` applied directly by `runner.js` to the visible `<canvas>` element (from `canvasPair.canvas`), not something `render.js` draws into the pixel buffer.
  Why: zero coupling with `render.js`'s drawing code; shake state (`shakeMagnitude`, decaying like squash via `Math.exp(-cameraShakeDecayRate * dt)`) lives entirely in `runner.js`, only the two new CONFIG tunables (`cameraShakeMax`, `cameraShakeDecayRate`) are shared.
- Decision: shake magnitude is set via `Math.max(current, beat.shake * cameraShakeMax)` on impulse, not additive — same "overwrite, don't accumulate" pattern as squash, for the same simplicity reason.
- Decision: added `CONFIG.renderFps` (12) and `CONFIG.speakLeadSeconds` (0.15) as named tunables rather than inline magic numbers, even though the PRD's Section 7 tuning list only explicitly names camera shake decay — keeps every knob in the one shared object per the "single mutable CONFIG" rule, in case the tuning pass wants to touch them too.

**Files Changed:** `physics.js` (CONFIG: `cameraShakeMax`, `cameraShakeDecayRate`, `speakLeadSeconds`, `renderFps`), `runner.js` (created), `preview.html` (rewritten to fetch real beats and delegate to `runFight()`)

**Backtrack Notes:** `runner.js` is new and additive — reverting means deleting the file and the 4 new CONFIG keys; `preview.html` would need its old inline loop restored (see prior WORKLOG entries' versions) or just re-fetch working directly against `physics.js`/`render.js` as it did before this entry.

## [T+~35] index.html — real shell + live CONFIG slider panel

**Status:** completed

**Summary:** Built the final `index.html`: hardcoded Tombstone vs. Minotaur matchup (bot selector is PRD's cut-order item #3, not needed for tonight), loads `sample_beats.json` via `fetch()`, wires the sprite-fallback + `runFight()` exactly like `preview.html`, and adds a right-hand debug panel with 21 live `<input type=range>` sliders — one per "feel" `CONFIG` value, generated from a `[key, min, max, step]` table rather than 21 hand-written blocks. Total across all 5 Stream B files (`physics.js`, `render.js`, `runner.js`, `index.html`, `preview.html`) is 459 lines.

**Decisions & Reasoning:**
- Decision: excluded `worldW`, `worldH`, `floorY`, `wallLeft`, `wallRight`, `pixelScale`, and the color/palette fields from the slider panel, even though the brief said "every value in CONFIG."
  Why: the first group is baked into canvas pixel dimensions at `createCanvasPair()` time — sliding them post-creation wouldn't resize anything, it'd just desync the physics arena from the drawn canvas. Colors don't map to a `<input type=range>` sensibly. Everything else (gravity, restitution, damping, botRadius, rotation quantization, all eye params, squash params, camera shake, speak lead, render fps) — 21 values — is live-tunable.
- Decision: kept `preview.html` alongside `index.html` rather than deleting it.
  Why: no reason to remove a working, simpler harness; if `index.html` breaks during later edits, `preview.html` still isolates physics+render+runner without the slider-panel DOM code.

**Files Changed:** `index.html` (created)

**Backtrack Notes:** Self-contained new file; deleting it has no effect on anything else. If a specific slider misbehaves (e.g. `botRadius` dragged small enough that eyes sit outside the body), that's an expected interaction between independently-tunable values, not a bug — fix by also adjusting `eyeOffsetX/Y` in the same session.

## [T+~50] .env created, demo.html (zero-network fallback), bot picker on index.html

**Status:** completed

**Summary:** Three things: (1) created a local `.env` from the already-merged `.env.example` (still gitignored, empty `BRIGHTDATA_API_KEY` for the user to fill in — `1_scrape.py` hasn't actually been run anywhere, confirmed by checking `data-scrape` branch, `main`, and local disk: no `raw/`, `data/`, or scraped output exists). (2) Built `demo.html` — a copy of `index.html` with `sample_beats.json`'s content inlined via `<script type="application/json">` instead of `fetch()`, so it has zero network dependency at all; this is the actual safety net for tonight, not `index.html` itself. (3) Added a bot picker (two `<select>`s + Fight! button) to `index.html`: tries `fetch('./raw/groups.json')` for the real 24-bot roster, falls back to `['Tombstone', 'Minotaur']` if that file doesn't exist (it doesn't, yet) — picking different names re-skins sprites/captions via simple string substitution (`beat.line`/`beat.fact`, `.split().join()`, not regex) since `sample_beats.json`'s actual impulse choreography is only authored for Tombstone vs. Minotaur. Added a small `runner.js` change (`runFight()` now returns `{ stop() }`) so `index.html` can cleanly kill the previous RAF loop before starting a new one on each "Fight!" click.

**Decisions & Reasoning:**
- Decision: `demo.html` is a separate file from `index.html`, not a mode/flag on the same file.
  Why: keeps the zero-network guarantee absolute and easy to reason about — no risk of a code path in the "safe" demo file accidentally depending on `fetch()`. `index.html` keeps evolving (bot picker, future features); `demo.html` should stay frozen and boring.
- Decision: bot-name substitution is plain `string.split(x).join(y)`, not a regex replace.
  Why: avoids any regex-special-character risk if a real scraped bot name ever contains characters like `(`, `)`, `.` etc.
- Decision: when the picked names aren't Tombstone/Minotaur, show a small note under the picker stating the choreography is still Tombstone-vs-Minotaur under the hood.
  Why: the substitution is cosmetic only (captions/sprites), not a new generated fight — surfacing that plainly avoids the demo accidentally implying live generation that isn't happening.
- Decision: `runFight()` returns a `stop()` handle rather than `index.html` reloading the whole page on each Fight! click.
  Why: reload would also re-fetch `raw/groups.json`/`sample_beats.json` unnecessarily and reset the CONFIG sliders back to defaults, losing any live tuning — a small in-place stop/restart preserves both.
- Decision: confirmed (again, via fresh `git fetch`) that no scraped data exists anywhere reachable — user had been told "all the data has been fetched" but this doesn't hold in this repo/environment. Flagged to user directly rather than silently proceeding as if it were true.

**Files Changed:** `.env` (created, gitignored), `demo.html` (created), `index.html` (picker UI + `startFight()`/restart logic), `runner.js` (`runFight()` now returns `{ stop() }`)

**Backtrack Notes:** `demo.html` is fully standalone — deleting it affects nothing else. The `index.html` picker is additive; reverting means removing the `#picker`/`#pickerNote` markup and the `startFight`/`populateSelect`/`botsPromise` block, restoring the single hardcoded `fetch('./sample_beats.json').then(...).then((fight) => runFight(...))` call. `runFight()`'s returned `stop()` is backward compatible — any caller ignoring the return value (e.g. `preview.html`, `demo.html`) behaves exactly as before.

## [T+~60] Built Stream A's missing piece: beats.js + speak.js + live generation

**Status:** completed

**Summary:** User explicitly authorized crossing the original Stream A/B file boundary (`beats.js`/`speak.js`/`prompts/` were off-limits all session per the kickoff brief) after confirming the real scraped data (`data/bots.json`, `data/fights.json`, `raw/groups.json`) had landed but the generation layer described in PRD Section 3 still didn't exist anywhere. Built: `beats.js` (fight-history summarizer + one Claude Opus 5 call with a JSON-schema structured output + a hand-written validator + retry-once + fallback to `sample_beats.json`, per PRD Section 3's exact spec) and `speak.js` (`window.speechSynthesis` wrapper handling the documented `getVoices()`/`voiceschanged` async-load gotcha). Wired both into `index.html`: an API-key input (localStorage-persisted) that, when filled in, routes the Fight! button through `generateFight()` instead of the existing sample-beats text-substitution reskin.

**Decisions & Reasoning:**
- Decision: call the Anthropic Messages API directly from the browser via `fetch()` with the `anthropic-dangerous-direct-browser-access: true` header, rather than using the official SDK or standing up a backend.
  Why: the project's hard constraint is no build step / no `npm install` / no server beyond the static file server already in use — there's no way to run an installable SDK or a key-holding backend under those constraints. This means the user's API key is visible in the browser (anyone opening dev tools can read it) — acceptable for a local hackathon demo where the user controls their own key and the page isn't deployed publicly, but genuinely not safe for any public deployment. Flagged this plainly rather than silently building it in.
  Alternatives considered: a tiny local proxy server to hide the key — rejected, adds a moving part and violates "no server beyond static files" for a demo that doesn't need to survive past tonight.
- Decision: used `output_config: {format: {type: "json_schema", schema: BEAT_SCHEMA}}` (structured outputs) instead of relying purely on prompt instructions + defensive fence-stripping.
  Why: PRD Section 3 asks for "demand JSON only... strip fences defensively anyway" — structured outputs make the JSON-shape guarantee actually enforced by the API rather than hoped-for, while the *values* within that shape (ascending `t`, magnitude bands, gap spacing) still can't be schema-enforced (no numeric range support in Anthropic's structured-output schema), which is exactly why a separate `validateFight()` step still exists per the PRD's explicit design.
- Decision: `generateFight()` does its own retry-once-then-fallback internally (2 total attempts, then `fetch('./sample_beats.json')`), matching PRD Section 3 literally, rather than surfacing retry logic in `index.html`.
  Why: keeps `index.html` a thin caller; the fallback behavior is identical to what's already been true all session (sample_beats.json as safety net), so no new failure mode for the demo.
  Alternatives considered: surfacing a "regeneration failed, using sample fight" banner to the user — skipped for time; `console.warn` calls exist at each failure point if this needs debugging later.
- Decision: added a `fightGeneration` counter in `index.html` so a stale in-flight `generateFight()` call (which can take several seconds) can't clobber a newer fight if the user clicks "Fight!" again before the first call resolves.
  Why: cheap to add, avoids a real race condition given generation is now async and slow (unlike the instant synchronous reskin path).
- Decision: did not create a `prompts/` directory — the system prompt lives as a `SYSTEM_PROMPT` string constant inside `beats.js`.
  Why: avoids one more `fetch()` dependency (consistent with the demo.html zero-network lesson) for content that doesn't need to be a separate file at this scale.

**Files Changed:** `beats.js` (created), `speak.js` (created), `index.html` (API key input + async `startFight()` with live-generation branch)

**Backtrack Notes:** Fully additive and optional — leaving the API key field empty preserves the exact prior behavior (sample-beats + text-substitution reskin), byte-for-byte. To revert entirely: remove the `beats.js`/`speak.js` imports and the API-key UI/branch from `index.html`, restoring the synchronous `startFight()` from the previous entry. `runner.js` needed no changes — its `speak()` wrapper already checked for `window.speak` defensively, so `speak.js` just had something to attach to.

## [T+~65] Reconciled with partner's independent beats.js/speak.js, removed API-key UI

**Status:** completed

**Summary:** Re-fetched `data-scrape` and found the partner had independently built their own `beats.js`/`speak.js` (classic non-module scripts, `window.Beats`/`window.Speak` globals, data pre-bundled into `data/data.js` by their `3_embed.py`, plus `prompts/beats_system.txt`) — a direct collision with the ES-module versions built in the previous entry. Compared both for the user; user chose to **take the partner's versions** and adapt Stream B's wiring rather than keep mine. Removed my `beats.js`/`speak.js`, merged `origin/data-scrape` cleanly (no conflict once the paths were free), then rewired `index.html`: added classic `<script>` tags for `data/data.js` → `beats.js` → `speak.js` (order matters — `beats.js`'s top-level `const DATA = window.OOF_DATA` needs `OOF_DATA` set first), a `window.speak = window.Speak.speak` shim so `runner.js`'s existing check works unchanged, fetched `prompts/beats_system.txt` and `sample_beats.json` into `window.OOF_SYSTEM_PROMPT`/`window.OOF_SAMPLE_BEATS` (both read lazily inside `Beats.generate()`, so an async fetch before first use is fine), and switched the bot-picker dropdowns to read `window.OOF_DATA.bots` directly instead of fetching `raw/groups.json` separately. Also removed the API-key input field entirely per explicit user instruction — `Beats.generate()` now handles the key via its own `localStorage`-backed `prompt()` popup on first use.

**Decisions & Reasoning:**
- Decision: kept my own text-substitution reskin logic, but scoped it to only the `source === 'fallback'` case (i.e., only when `Beats.generate()` itself fell back to `window.OOF_SAMPLE_BEATS`), rather than removing it entirely.
  Why: `OOF_SAMPLE_BEATS` is always the frozen Tombstone-vs-Minotaur fixture regardless of which two bots were actually picked in the dropdown — without relabeling, a failed generation for e.g. "Witch Doctor vs Ribbot" would silently play captions saying "Tombstone"/"Minotaur", which reads as a bug rather than an honest fallback.
  Alternatives considered: dropping the substitution and just accepting the mismatch on fallback — rejected, it's a small addition and meaningfully improves the failure-mode experience.
- Decision: did not question or push back on removing the API-key input field, even though it meant reintroducing an intrusive `prompt()` popup UX — this was an explicit, unambiguous user instruction.
  Why: not a judgment call — the user said "remove the front-end api input field" directly.
- Decision: left the user's own uncommitted local work (`scripts/4_images.py` deleted, new untracked `image-scripts/` directory with an expanded `1_scrape.py`/`2_extract.py`/`3_analyze.py`/`4_images.py` pipeline) completely untouched — not staged, not committed, not investigated further.
  Why: that's the user's own in-progress work on a separate task (the 24-bot sprite pipeline), unrelated to this reconciliation; committing it without being asked risks folding half-finished work into an unrelated commit.

**Files Changed:** `beats.js` (deleted mine, replaced via merge with the partner's), `speak.js` (same), `data/data.js` (new, from merge), `prompts/beats_system.txt` (new, from merge), `index.html` (rewired for classic-script globals, API-key UI removed), `CLAUDE.md`, `WORKLOG.md`

**Backtrack Notes:** To revert to the ES-module version from the prior entry: restore that entry's `beats.js`/`speak.js` from git history, revert `index.html`'s `<script>` tags back to `import` statements, restore the `apiKeyInput` UI block and `startFight()`'s branching logic. The merge commit bringing in the partner's files is `origin/data-scrape`'s tip at merge time — `git log` on this branch shows exactly which commit.

Stream B (`physics.js`, `render.js`, `runner.js`, `index.html`) is feature-complete per PRD Section 4: integrator, floor/wall restitution+damping, googly eyes, squash/stretch, beat playback with captions/speak/camera-shake, and a live-tunable debug panel — all developed and verified against the frozen `sample_beats.json`. Per PRD Section 6, next step is swapping in Stream A's `generated_beats.json` and running the 3-point merge check (schema validation, magnitude sanity, timing/caption sync) — not yet done, waiting on Stream A.

## [T+~75] Fixed live-generation validation failure; added "Play Sample Fight" button

**Status:** completed

**Summary:** User reported every "Fight!" click was falling back to the sample fixture. Diagnosed by writing a standalone Python script (`/tmp/beats_diagnostic.py`, deleted after use) that replicates `beats.js`'s exact `botSummary()`/prompt/API-call/`validate()` logic outside the browser, run with the user's real API key supplied directly (used only in-memory for these diagnostic calls, never written to disk or committed). Root cause: the model was reliably emitting a "scene-setting" opening beat with a zero impulse (`{x:0,y:0}`, `spin:0`) before the first real hit, which fails `validate()`'s magnitude check on every single generation. Fixed by adding one explicit rule to `prompts/beats_system.txt`: every beat must carry a real, non-zero impulse — no narration-only beats. Verified fixed with a clean re-run (0 validation errors) on Tombstone vs. Minotaur. A second, unrelated matchup (Witch Doctor vs. HUGE) hit one rare boundary case (impulse magnitude landing right at the 220 upper cutoff via floating-point rounding) on one of two runs — not fixed further, since `Beats.generate()`'s existing retry-once + fallback already exists to absorb exactly this kind of occasional miss.

Also added a **"Play Sample Fight" button** next to "Fight!" in `index.html`, per user request: it skips `Beats.generate()`/the API entirely and plays the relabeled sample fixture directly, as a guaranteed-to-work option independent of live-generation issues.

**Decisions & Reasoning:**
- Decision: diagnosed by porting the exact JS logic to a throwaway Python script and calling the real API directly, rather than trying to debug through the browser console.
  Why: no browser-automation tool is available in this environment (confirmed via ToolSearch — only Figma/Notion/Slack MCP tools and WebFetch), and copy-pasting collapsed console array/object output to relay back and forth proved unreliable across several attempts (Chrome's console renders nested arrays as collapsed objects that don't survive a plain-text copy). Replicating the logic server-side got a definitive answer in one shot.
  Alternatives considered: kept trying console-based approaches (multi-line paste, `copy()`, "Copy object") — abandoned after three failed rounds, each hitting a different browser/UI quirk (syntax errors from paste mangling, no "Copy object" menu item, etc.).
- Decision: fixed the root cause in the prompt (`prompts/beats_system.txt`) rather than loosening `validate()` to tolerate zero-impulse beats.
  Why: PRD's beat schema ties every beat to a physical impulse event synchronized with commentary — a "beat" with no impulse isn't a beat in that model's terms, it's cosmetic narration that doesn't belong in the array at all. Tightening the instruction (attach intro lines to the first real hit instead) is the correct fix, not carving out an exception in the validator.
- Decision: did not attempt to fix the rarer 220-magnitude boundary case.
  Why: non-deterministic, low-frequency, and a re-run of the same matchup passed clean — the existing retry-once mechanism already covers this without further changes. Chasing single-beat boundary misses further would cost more API calls than it's worth right now.

**Files Changed:** `prompts/beats_system.txt` (added the no-zero-impulse rule), `index.html` (added "Play Sample Fight" button + `createBodies()`/`relabelFight()`/`playFallback()` helpers, refactored `startFight()` to share them)

**Backtrack Notes:** The prompt fix is a single added bullet in `prompts/beats_system.txt`'s RULES section — trivial to revert if it turns out to cause other issues. The fallback button is fully additive (`playFallback()` reuses `relabelFight()`/`createBodies()` already used by `startFight()`); removing the button and its listener fully reverts it.

## [T+~85] Built the Pro League image scraper, fixed a zero-zone Bright Data account

**Status:** completed

**Summary:** Built `image-scripts/5_proleague_images.py` to scrape `https://battlebots.com/proleague/` for every `<img>` tag's URL + surrounding metadata (alt, title, nearest `<figcaption>`, nearest preceding heading for section context, page URL) — one row per image, output to both `raw/proleague_images.csv` and `.json`. Researched "Bright Data Studio" first: confirmed it's Bright Data's Scraper Studio product, which requires a pre-built Collector (configured through their web IDE) — not something scriptable cold without first creating a collector by hand. User chose to skip Studio and reuse the Web Unlocker pattern already proven in `1_scrape.py`/`image-scripts/1_scrape.py` instead. First run failed with `zone "web_unlocker1" not found` — turned out this Bright Data account had **zero zones configured at all** (`GET /zone/get_active_zones` returned `[]`). Creating one via `POST /zone` first failed with a 403 (API key lacked Admin/Ops permission); user fixed the key's role and rotated it; retried and the zone created successfully. Scraper then ran clean: 30 images found, one filtered out (a Facebook tracking pixel, not real content) → 29 real images in the final output.

**Decisions & Reasoning:**
- Decision: reused the existing `unlock()` / Web Unlocker POST-to-`/request` pattern from `1_scrape.py` rather than building against Scraper Studio's collector API.
  Why: user's explicit choice after being told Scraper Studio needs a pre-configured Collector ID that doesn't exist for this page — the Web Unlocker approach needed zero new Bright Data setup beyond a working zone (which turned out to be the actual blocker anyway).
  Alternatives considered: building a Scraper Studio collector via their AI-agent-assisted web IDE — rejected as a manual, out-of-band step with no API entry point to do it cold.
- Decision: created the missing zone via Bright Data's `POST /zone` API (`plan.type: "unblocker"`) rather than asking the user to click through their dashboard, once they explicitly confirmed and fixed the permission issue.
  Why: user's explicit "create a zone based on API" instruction, after being warned this is a real account-level change (not local/reversible-by-me) and given the dashboard alternative.
- Decision: named the new zone `web_unlocker1` (matching the pre-existing `.env`/`.env.example` value) rather than picking a new name.
  Why: zero code changes needed elsewhere — every existing script already reads that exact zone name.
- Decision: filtered out known analytics/tracking-pixel domains (`facebook.com/tr`, Google Analytics, Doubletree, GTM) from the results rather than leaving every raw `<img>` tag in.
  Why: a 1x1 Facebook conversion-tracking pixel isn't a "real" content image by any reasonable reading of "extract all image URLs" — false-positive noise, not signal.
- Decision: prefer `data-src`/`data-lazy-src`/`data-original`/`data-srcset` over a bare `src` attribute when resolving each image's URL.
  Why: many modern sites (this one included, WordPress + lazy-loading) put a placeholder/blur-up image in `src` and the real URL in a `data-*` attribute — reading `src` alone would return placeholder URLs, not the actual images.

**Files Changed:** `image-scripts/5_proleague_images.py` (created), `raw/proleague_images.csv` (created), `raw/proleague_images.json` (created). Also: created a new Bright Data zone named `web_unlocker1` on the user's Bright Data account (external side effect, not a repo file, but recorded here since it's load-bearing for this and every other Web Unlocker-based script in the repo going forward).

**Backtrack Notes:** The scraper is a standalone, additive script — deleting it and its two `raw/` outputs fully reverts this entry. The Bright Data zone is external infrastructure, not something `git revert` touches — if it needs to be removed, that's a dashboard/API action on Bright Data's side, not a code change.

## [T+~95] Sprite-art detour: fixed 4_images.py, then a chain of provider access blockers

**Status:** completed (commentary provider switch) / blocked (image gen)

**Summary:** User asked for per-bot sprite art + an arena background image, "axonometric 45-degree bird's-eye view," generated from real reference photos via an image-generation API. Working backward from `image-scripts/4_images.py`'s own comment ("Next: feed sprites/source/*.jpg to AI Studio, save results to sprites/pixel/") confirmed the intended source is per-bot Fandom lead-image photos, not the just-scraped `raw/proleague_images.*` (which turned out to be mostly page graphics/merch/cast photos, not individual bot photos — confirmed by inspecting the 4 ambiguous `.avif` rows, whose `nearby_heading` was "GET SOME MERCH"). `4_images.py` had never actually been run and had two bugs against the current repo state: (1) no `load_dotenv()` call, (2) `raw/groups.json`'s bot-list extraction assumed the old flat `{groupLetter: [bots]}` shape, but the real file (from the Stream A merge) is the newer `{season, groups, bots, matchups}` shape — fixed both, plus a third bug found while running it: the MediaWiki multi-title `|` separator wasn't percent-encoded, which Bright Data's request validator now rejects outright (fixed with `urllib.parse.quote`). Ran clean for Tombstone + Minotaur (2/24, per the script's own "DO THIS FIRST" guidance) — downloaded to `sprites/source/`, confirmed via `file` to actually be WebP bytes despite the `.png` extension (Fandom serves WebP regardless of URL).

Then hit a chain of three separate provider-access blockers, each diagnosed by installing the real SDK and testing live rather than guessing:
1. **Google Gemini** (`google-genai`): WebFetch on Google's own docs pages returned a fabricated `client.interactions.create()` API on two separate fetches — caught by cross-checking against the actual installed SDK (`dir(genai.Client())` has no `interactions` attribute; real methods are `models.generate_content`/`generate_images`/`edit_image`). Model ID `gemini-3.1-flash-image` genuinely exists (confirmed via live `client.models.list()`), but every image-capable model returned `429 RESOURCE_EXHAUSTED` — free-tier quota of 0 for all image generation, requires billing enabled on the linked Google Cloud project. Not yet resolved (user's choice pending).
2. **OpenAI images** (`openai` SDK): user's API key turned out to be Codex-scoped — `client.models.list()` shows exactly 5 accessible models (`gpt-5-codex`, `gpt-5.3-codex`, `gpt-5.4`, `gpt-5.5`, `gpt-5.6-sol`), zero image models, regardless of which model ID was requested (`gpt-image-2`, `gpt-image-1` both 403 "does not have access"). Not a billing issue like Google's — this key structurally cannot do image generation.
3. **ChatGPT Plus subscription**: not viable at all — Plus is a consumer product (chat.openai.com), entirely separate from API billing (platform.openai.com). No token/session from a Plus subscription authenticates against the Images API.

Given (2) confirmed 5 real *text* models were accessible, pivoted to using this same OpenAI key for the **live commentary generation** instead (replacing the Claude Opus 5 call in `beats.js`), per explicit user instruction. Verified live against the exact real system prompt + two different matchups (Tombstone/Minotaur, Witch Doctor/HUGE) — both passed `validate()` with 0 errors on `gpt-5.5`.

**Decisions & Reasoning:**
- Decision: cross-checked Google's WebFetched documentation against the actual installed `google-genai` SDK (`dir()`/`inspect.signature()`) before writing any code, rather than trusting the doc-page summaries.
  Why: two independent WebFetch calls to the same Google docs URL both confidently described a `client.interactions.create()` method with specific quoted branding ("Nano Banana 2") that simply doesn't exist on the real installed package — a clear case of a doc-summarization pass either hallucinating or reading a stale/incorrect cached version. The GitHub README fetch and local SDK inspection agreed with each other and directly contradicted the two docs-page fetches, so empirical verification won over documentation.
- Decision: picked `gpt-5.5` (not `gpt-5-codex`/`gpt-5.3-codex` or `gpt-5.6-sol`) for commentary generation, from the 5 available models.
  Why: commentary/JSON-beat generation is a general instruction-following + creative-writing task, not a coding task — the Codex-tuned variants are optimized for agentic coding use, and `5.6-sol` is an unfamiliar/unverified variant; `gpt-5.5` is the most recent plain general-purpose model in the accessible set.
- Decision: renamed the `localStorage` key from `oof_api_key` to `oof_openai_api_key` when switching providers, rather than reusing the same key name.
  Why: the old key name already held the user's real Anthropic key from earlier testing — reusing the name would silently send an Anthropic-formatted key to OpenAI's API on the first call after the switch (guaranteed 401, confusing to debug) instead of cleanly re-prompting for the right credential.
- Decision: did not attempt any workaround for the ChatGPT Plus request — stated plainly that it's not possible via API, rather than trying something known not to work.
  Why: Plus and API billing are genuinely separate products with no shared auth path; attempting it would just waste a round-trip on something with zero chance of succeeding.

**Files Changed:** `image-scripts/4_images.py` (added `load_dotenv()`, fixed `raw/groups.json` shape compatibility, percent-encoded the MediaWiki multi-title URL), `sprites/source/Tombstone.png`, `sprites/source/Minotaur.png` (downloaded reference photos, actually WebP bytes), `beats.js` (Anthropic → OpenAI: endpoint, auth header, request/response shape, `localStorage` key renamed, model `gpt-5.5`)

**Backtrack Notes:** The `4_images.py` fixes are backward-compatible (still handles the old flat `groups.json` shape via the `isinstance`/`"bots" in groups` check) and don't affect anything else in the pipeline. The `beats.js` provider switch is a straightforward revert to the prior WORKLOG entry's Anthropic version if needed — no other file depends on which provider `beats.js` uses internally, only on its public `Beats.generate()`/`validate()`/`botSummary()` shape, which is unchanged. Image generation (sprites + arena) remains blocked pending either Google Cloud billing or a general-purpose (non-Codex) OpenAI key with image-model access — not something I can route around further without new credentials.

## [T+~100] Downloaded all 24 reference photos, wrote image-gen.md for external generation

**Status:** completed

**Summary:** Ran the now-fixed `image-scripts/4_images.py` for all 24 bots (previously only tested on 2) — clean 24/24 download to `sprites/source/`. Since image-generation API access is still blocked on every credential tried so far, user opted to run generation externally via Google Antigravity instead of waiting on API billing/key access. Wrote `image-gen.md`: a self-contained brief with the exact tested sprite prompt (axonometric/45°-bird's-eye, flat colors, bold outline, sized for a small nearest-neighbor-upscaled icon), a new arena-background prompt (matching the PRD's exact world geometry — 160×90, floor at y=78, walls at x=8/152, 16:9), the full 24-bot roster grouped by group letter, and the exact output paths/naming convention (`media/bots/<slug>.png`, `media/arena.png`) so dropping results in is the only wiring needed.

**Decisions & Reasoning:**
- Decision: derived the arena prompt's geometry constraints directly from PRD Section 2's numbers (160×90 world, floor y=78, walls x=8/x=152, 16:9 aspect) rather than a generic "battle arena" description.
  Why: if the generated background doesn't respect the actual world dimensions/margins, painted walls/floor lines won't align with where bots actually bounce in the physics sim — explicitly called out in the doc so whoever generates it (or reviews the result) knows what "correct" means here, not just "looks like an arena."
- Decision: noted that `media/arena.png` wiring into `render.js` (replacing the flat fill background) is an explicit follow-up, not done yet.
  Why: didn't want the doc to imply the code side is already handled — keeps the doc honest about what's actually wired vs. what's still a TODO.
- Decision: ran the full 24-bot download proactively (rather than waiting to be asked) once `4_images.py` was confirmed working on the 2-bot test.
  Why: removes a manual step between "here's the prompt" and "here's something to actually run it against" — the doc can point at complete, ready-to-use input files instead of a script the user still has to run themselves.

**Files Changed:** `image-gen.md` (created), `sprites/source/*.png` (22 new bot reference photos, completing the roster to 24/24), `sprites/manifest.json` (updated with all 24 entries)

**Backtrack Notes:** Purely additive — `image-gen.md` is documentation, the sprite photos are cached scrape output reproducible by re-running `image-scripts/4_images.py`. Nothing else in the repo reads `image-gen.md` or depends on it existing.

## [T+~105] Integrated 13 externally-generated bot sprites (transparency fix)

**Status:** completed

**Summary:** User generated bot sprite art externally per `image-gen.md`'s brief (via Google Antigravity, waiting on image-gen credit to reset for the rest) and dropped 13 of them straight into `media/bots/<slug>.png` with exactly the right filenames — no wiring needed on that front, `render.js`'s existing `loadSprite()`/fallback-to-blob mechanism already picks them up per-bot automatically. One real issue: every generated image had a solid white background (`RGB` mode, no alpha) rather than transparent — would have rendered as a white square behind the robot silhouette against the game's dark arena instead of blending in. Fixed by chroma-keying near-white pixels (`r,g,b > 240`) to transparent via Pillow, backing up each raw generated image to `sprites/pixel/<slug>.png` first (matching the pipeline's originally-documented convention). Verified: alpha-channel transparency percentage across all 13 lands in a consistent 55-66% band (centered robot silhouette against transparent background, no outliers/failures), and visually spot-checked Manta and Tombstone directly — both faithful to style brief, googly eyes will composite on top per the existing `drawBody()`/`drawEyes()` render order (unconditional, sprite-or-blob doesn't change eye drawing).

**Decisions & Reasoning:**
- Decision: backed up each raw (white-background) generated image to `sprites/pixel/<slug>.png` before overwriting `media/bots/<slug>.png` with the transparent version.
  Why: non-destructive — if the chroma-key threshold ever needs adjusting (e.g. a sprite with white paint on the robot itself getting incorrectly keyed out), the original is still there to reprocess from, rather than needing to regenerate via the image API again.
  Alternatives considered: processing in place with no backup — rejected, cheap insurance against a lossy one-way edit.
- Decision: used a simple brightness threshold (`r,g,b > 240`) for the chroma key rather than a more sophisticated background-removal approach (flood-fill from corners, edge detection, etc.).
  Why: the generation prompt explicitly asked for a plain white background with no gradients, and the outline is bold dark navy — a flat threshold cleanly separates the two color regimes for this art style without needing anything fancier. Spot-checked visually (Tombstone, Manta) and via alpha-percentage sanity check across all 13; no artifacts observed.

**Files Changed:** `media/bots/{manta,tombstone,cobalt,copperhead,disarray,jackpot,madcatter,magnitude,malice,skorpios,terrortops,the-twins,valkyrie}.png` (background stripped to transparent, in place), `sprites/pixel/*.png` (13 raw pre-transparency backups, new)

**Backtrack Notes:** Fully reversible per-file — copy the matching `sprites/pixel/<slug>.png` back over `media/bots/<slug>.png` to restore the raw white-background version. 11 bots still pending external generation (Bloodsport, DeathRoll, End Game, Golden Fury, HUGE, HyperShock, Minotaur, Orbitron, Ribbot, Switchback, Witch Doctor) — those fall back to plain colored blobs until generated, exactly per the sprite-hook's original graceful-degradation design.

## [T+~110] Bigger bots + re-proportioned eyes, tighter commentary pacing, collapsible CONFIG panel

**Status:** completed

**Summary:** Three rounds of user feedback in one pass. (1) Bots too small / eyes disproportionate: bumped `botRadius` 7 → 10, then user asked for "2x bigger" on top of that → 20. Eye values weren't just linearly rescaled with body size — also re-proportioned for a bolder "googly" look (pupil was only ~42% of socket diameter, widened toward ~57%), then scaled that whole re-proportioned set by the same 2x when `botRadius` doubled again (`eyeOffsetX` 3.0→4.0→8.0, `eyeOffsetY` -3.0→-3.5→-7.0, `eyeSocketRadius` 2.6→3.0→6.0, `pupilRadius` 1.1→1.7→3.4, `eyeClampRadius` 2.2→2.6→5.2). Widened the `botRadius`/eye sliders' ranges in both `index.html` and `demo.html` so the new defaults aren't clamped below their slider max. (2) Commentary pacing: user wants ~2s between beats (was ~0.8-1.9s from the model in practice). Tuned `prompts/beats_system.txt` in two rounds, verified live each time — round 1 ("aim for ~2s, aim for 18-22 beats") landed at 1.8s avg on one matchup but regressed badly on another (30 beats, 1.0-1.4s gaps — model defaulted to old max-beat-count habit when it had more real history to reference). Round 2 made both the spacing and beat-count-vs-duration-math explicit and forceful ("hard requirement, not a suggestion" / "beats × ~2.1s must land within 30-45s, so 18-21, NOT 25, NOT 30") — re-verified on the same problematic matchup: 22 beats, 1.4-2.5s range, 1.74s avg. Better and more consistent, but not landing exactly on 2.0s every time — accepted as reasonable given LLM instruction-following has inherent variance, not chasing further without a specific new complaint. Validator's hard gap floor (0.8s) intentionally left untouched — it's a safety net, not the pacing target, and tightening it would risk more validation failures/fallbacks. (3) CONFIG panel: wrapped in `<details>`/`<summary>` (native, no JS needed) in both `index.html` and `demo.html`, defaults open so behavior is unchanged unless the user collapses it.

**Decisions & Reasoning:**
- Decision: re-proportioned the eyes rather than doing a pure linear rescale when first asked to fix "proportion."
  Why: pure linear scaling would have preserved the exact same (too-small) pupil-to-socket ratio the user was complaining about — the actual fix was widening that ratio, which a linear scale can't do by definition.
- Decision: on the "2x bigger" follow-up, scaled the *already re-proportioned* eye values by 2x rather than re-deriving proportions from scratch.
  Why: the eye proportions were just approved implicitly by the user moving on to other requests — treat that as settled and carry it forward multiplicatively, not re-litigate it.
- Decision: pacing fix targeted the prompt text only, never the validator's gap-floor constant.
  Why: established pattern from the earlier zero-impulse bug — the validator is a safety net (catches genuinely broken output), the prompt is where "feel"/style targets belong. Loosening the floor to match the target exactly would turn ordinary LLM variance into validation failures.
- Decision: stopped pacing iteration after two rounds even though results don't hit exactly 2.0s every time.
  Why: diminishing returns — each iteration costs a real API call, and the trend (0.8-1.9s scattered → consistently 1.4-2.5s, avg ~1.7-1.8s) is a clear, meaningful improvement. Further chasing exact precision on a soft/subjective pacing target isn't worth more tuning calls without a concrete new complaint that it still feels rushed.
- Decision: used native `<details>`/`<summary>` for the collapsible panel instead of a JS-driven toggle.
  Why: zero JS needed, works identically in both `index.html` and `demo.html` (which don't share a script file), and matches this project's general bias toward the simplest thing that works.

**Files Changed:** `physics.js` (`botRadius` 7→20, eye CONFIG values re-proportioned and scaled), `prompts/beats_system.txt` (pacing/beat-count rules rewritten twice), `index.html` + `demo.html` (slider range widening for `botRadius`/eye configs, `<details>`/`<summary>` collapsible panel)

**Backtrack Notes:** All CONFIG changes are live-tunable via the sliders already — no restart needed to experiment further, and the exact prior values are in this entry if a full revert is wanted. The prompt changes are plain text edits to `prompts/beats_system.txt`, trivially revertable. The collapsible-panel markup change is cosmetic only; `#sliders` div (what the script populates) is unchanged, just now living inside a `<details>` instead of directly under `#panel`.

## [T+~112] Collapsed panel now actually frees layout space, not just hides content

**Status:** completed

**Summary:** First collapsible-panel pass (previous entry) only hid the sliders — `#panel`'s fixed `width: 280px` stayed put when collapsed, so the canvas area didn't reclaim any space. Fixed with `#panel:has(> details:not([open])) { width: auto; }` — when the details element inside is closed, the panel shrinks to fit just the "CONFIG (live)" summary text, and `#stage`'s existing `flex: 1` automatically expands the canvas area into the freed width. Applied to both `index.html` and `demo.html`. Added a `transition: width 0.15s ease` so the resize isn't an abrupt jump cut.

**Decisions & Reasoning:**
- Decision: used CSS `:has()` to key the panel's width off its child's open/closed state, rather than adding JS to toggle a class on `#panel` when the details element's `toggle` event fires.
  Why: zero JS needed (consistent with why `<details>`/`<summary>` was chosen in the first place), and `:has()` has been broadly supported (Chrome/Safari/Firefox) for long enough that it's a safe default now.

**Files Changed:** `index.html`, `demo.html` (both: `#panel` CSS only)

**Backtrack Notes:** Purely a CSS selector addition — removing the `:has()` rule reverts to the previous (content-hides-but-panel-stays-full-width) behavior with no other side effects.
