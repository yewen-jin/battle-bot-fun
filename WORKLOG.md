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

## Status: all 6 build stages complete, ready for T+40 merge

Stream B (`physics.js`, `render.js`, `runner.js`, `index.html`) is feature-complete per PRD Section 4: integrator, floor/wall restitution+damping, googly eyes, squash/stretch, beat playback with captions/speak/camera-shake, and a live-tunable debug panel — all developed and verified against the frozen `sample_beats.json`. Per PRD Section 6, next step is swapping in Stream A's `generated_beats.json` and running the 3-point merge check (schema validation, magnitude sanity, timing/caption sync) — not yet done, waiting on Stream A.
