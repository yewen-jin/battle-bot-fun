# PRD — OOF: The BattleBots Pro League, Re-enacted Badly

**Status:** hackathon build complete. This document originally governed a ~2h build sprint (demo at 21:00); it has been updated post-build to describe what actually shipped, so it can serve as the baseline for extension work. Sections below are marked where the built system diverges from the original plan — see `WORKLOG.md` for the decision-by-decision history of each divergence.

**Original build window:** ~2h. **Team:** 2 people, working in parallel from minute zero.
**Deliverable (as shipped):** `index.html`, served from a local dev server (`python3 devserver.py` — see below), no build step, no framework. `demo.html` is a zero-beat-generation-network fallback copy.

---

## 1. Product

Pick any two of the 24 Pro League bots. Get a cartoon re-enactment of their fight: two googly-eyed pixel blobs bouncing around an arena, with sports commentary that is factually grounded in eight seasons of real fight records.

The joke is register mismatch. Broadcast-voice commentary, real stats underneath, and what you're watching is two anxious potatoes falling over.

### Why this shape

The event brief promises a scrapeable season of results. It isn't there — the BattleBots wiki carries a standing spoiler ban on Pro League outcomes, and the episodes are still dropping weekly on YouTube. What exists is the 2026 fight card with unknown results, plus deep historical records for the same 24 bots.

So this is not a recap of fights that happened. It's a **dramatisation of fights that haven't aired yet**, built on what the historical record supports. The model says Tombstone takes this one by KO around ninety seconds; the cartoon shows you that, badly.

### Success criteria (updated post-build)

1. ~~Opens in a browser and plays a full fight without touching the network.~~ **Superseded.** Live beat generation (OpenAI) and TTS (Cartesia) are both live API calls now — the "no network" guarantee was traded away deliberately when browser `speechSynthesis` was replaced with a real cloud voice. `demo.html` still guarantees the *beat generation* call never happens (plays the frozen sample fight), but its audio still goes over the network via Cartesia. **Current criterion:** opens in a browser via `python3 devserver.py` and plays a full fight; a true zero-network fallback no longer exists, and reintroducing one is a real feature (see "what's next").
2. At least one person watching it laughs out loud. (Unchanged — subjective, not yet confirmed by demo.)
3. The commentary references a real, checkable fact from the bots' histories. (Unchanged — enforced by validator + prompt, "at least 3 lines" rule.)
4. ~~Runs in under 45 seconds end to end.~~ **Superseded.** Actual fight duration is **70-130 seconds**. The original 45s budget was implicitly sized for instant browser TTS; once real Cartesia audio duration was measured (~4s of spoken audio for a 60-char line), beats had to spread out to ~4.0-4.5s apart or lines cut off mid-sentence. **Current criterion:** runs in under ~2.5 minutes end to end.

---

## 2. The contract

**Everything hangs off one artifact: a beat array.** Stream A produces it, Stream B consumes it. Agree this in the first five minutes and neither person can block the other for the rest of the night.

### Critical rule

Each beat carries **both** the physics impulse and the commentary line spoken over it. One array, one source of truth.

Do not build a commentary track and a physics track separately. They will drift, the voice will say "airborne" a beat before the bot leaves the ground, and it looks broken in a way audiences notice instantly.

### World units

Fixed so impulse magnitudes mean the same thing on both sides of the seam.

| Thing | Value |
|---|---|
| World | 160 × 90 units, origin top-left, **+y is down** |
| Floor | `y = 78` |
| Walls | `x = 8` and `x = 152` |
| Bot radius | **20 units** (was ~7 at kickoff — grown through two user-requested size passes; eyes were re-proportioned, not linearly rescaled, to keep the googly-eye look at the new scale) |
| Gravity | 420 u/s² |
| Restitution | 0.55 floor, 0.60 walls, **0.60 bot-vs-bot** (new — see §4) |

### Impulse scale

Velocity added instantly, in units/sec. Calibrated so a massive hit launches a bot roughly 38 units — about half the arena height.

| Severity | \|impulse\| | spin (rad/s) | shake |
|---|---|---|---|
| glancing | 50–70 | 4–8 | 0.2 |
| solid | 100–140 | 10–16 | 0.5 |
| massive | 160–200 | 20–28 | 1.0 |

### Schema

```jsonc
{
  "fight": { "a": "Tombstone", "b": "Minotaur", "winner": "a", "method": "KO" },
  "beats": [
    {
      "t": 1.2,                              // seconds from start, ascending
      "target": "b",                         // "a" | "b" | "both"
      "impulse": { "x": 380, "y": -520 },    // u/s, +x right, -y up
      "spin": 14,                            // rad/s, + is clockwise
      "shake": 0.8,                          // 0–1 camera shake
      "line": "OH! Minotaur is airborne!",   // spoken + captioned
      "fact": "WC VII, KO at 1:52"           // optional, shown small
    }
  ]
}
```

### Rules

- `t` strictly ascending, first beat `t ≥ 0.5`
- 18–30 beats, total duration **70–130s** (was 30-45s — see success criterion 4 above; the 18-30 beat count is unchanged, only the pacing math around it moved)
- Gap between beats **target ~4.0-4.5s** (was ~0.8-1.5s in practice); the original **`≥ 0.8s` floor is kept in the validator as a hard safety net**, not as the pacing target — real spoken Cartesia audio needs the wider gap to avoid cutting a line off mid-sentence
- `line` under 90 characters
- Final beat should have `target` = loser, a massive impulse, and `shake: 1.0`
- Valid bot names only, from `data/data.js`'s bot roster (superseded `raw/groups.json`, which was the pre-merge placeholder — see §3)

### Committed at T+5

`sample_beats.json` — a hand-written 20-beat fight, schema-valid, never regenerated. Stream B develops against this exclusively. It is also the fallback demo.

---

## 3. Stream A — data to beats

**Owner:** partner. **Files:** `beats.js`, `speak.js`, `prompts/beats_system.txt`, `data/data.js`

Turns real fight history into a beat array, and speaks it.

### Scope (as shipped — two provider swaps from the original plan)

- Load `data/data.js` (`window.OOF_DATA` — classic script, set at page load, bundled by the partner's `3_embed.py`; supersedes the originally-planned separate `data/bots.json` + `data/fights.json` + `raw/groups.json` fetches)
- Build a compact fight-history summary for two named bots
- **One OpenAI (`gpt-5.5`) API call** → beat array conforming to the schema above. *Changed from Anthropic*: the switch happened as a side-effect of a sprite/arena image-generation credential hunt (Anthropic/Google image APIs were blocked on this account; the OpenAI key on hand had no image access either, but did have working text models) and was kept afterward since `gpt-5.5` validated cleanly. No functional reason to prefer it over Anthropic beyond "already had working access" — revisit if desired.
- Validate output: ascending `t`, gaps ≥ 0.8s (floor, not target — see §2), magnitudes in range, beat count 18-30, **duration ≤ 140s** (was 45s), names valid. On failure, retry once, then fall back to `sample_beats.json`
- **`Speak.speak(line)`, backed by Cartesia cloud TTS** (voice: "Clive — Measured Expert"), *not* `window.speechSynthesis`. Lines are queued via a promise chain — each line plays to its `ended`/`error` event before the next one starts fetching, so commentary can never overlap or cut off, even if beats arrive close together. API key is entered once via a `prompt()` popup and cached in `localStorage` (no on-page input field, per explicit instruction) — same pattern `beats.js` uses for its own key.
- Fallback screen recording at T+80 — not done; superseded by `demo.html`, which is the live, working zero-generation-network fallback.
- 30-second demo script — see §9, unchanged from original plan.

### Prompt design notes

- Demand JSON only. No preamble, no markdown fences. Strip fences defensively anyway.
- Put the impulse scale table directly in the system prompt.
- Instruct: commentary is straight and serious, the *physics* is the joke. Never wink at the audience.
- Require at least three lines to reference a specific real fight from the supplied history.
- Ask for a slow build — glancing hits early, massive at the end.

### Known gotcha (historical)

`speechSynthesis.getVoices()` returns an empty array on first call; wait for `voiceschanged` before selecting a voice. **No longer applicable** — `speak.js` no longer uses `window.speechSynthesis` at all (see above), so this gotcha doesn't apply to the current build. Left here for the record since it cost real time before the TTS backend changed.

### Known gotcha (current)

Cartesia TTS round-trip latency is ~0.7-0.75s per line (measured live, not assumed) — `speakLeadSeconds` (now 0.9, was 0.15 under browser TTS) compensates so audio doesn't land after the impulse it describes. If the TTS backend or voice ever changes again, re-measure this rather than reusing the old constant.

---

## 4. Stream B — beats to pixels

**Owner:** you. **Files:** `physics.js`, `render.js`, `runner.js`

Plays a beat array as animated pixel-art physics.

### Scope

**Integrator.** Fixed timestep, 1/60s. Accumulate real elapsed time, step in fixed chunks, clamp the accumulator to 0.25s. Variable `dt` makes springs explode the moment a frame drops or someone tabs away — and that will happen during the demo.

Per bot: `{x, y, vx, vy, angle, av}`. Each step apply gravity, integrate, then clamp against floor and walls with restitution. Ground contact also damps: `vx *= 0.82`, `av *= 0.70`.

**Impulses.** A beat adds directly to `vx/vy/av`. Nothing else drives motion between beats — no keyframes, no tweens on the bodies. All arcs, tumbles and bounces are emergent. **One addition beyond this:** right before a beat's impulse is applied, `snapToContact(a, b)` (new, in `physics.js`) pulls both bodies to exactly `botRadius*2` apart along their current relative direction. The beat schema has no positional data (immutable per §2), so between beats the two bodies drift independently and can end up nowhere near each other by the time a hit-beat fires — narration would describe a clash that visually isn't happening. The snap is a clash-cut, not a teleport (masked by the same-frame camera shake + squash), and only ever fires at the instant of impact.

**Bot-vs-bot collision (new, not in the original plan).** §8 originally listed "hull collision solving" as out of scope, meant to rule out general polygon-vs-polygon solving. What's actually needed here is simpler: both bots share the same fixed `botRadius`, so `resolveBotCollisions()` runs a single circle-vs-circle pass once per `step()`, after floor/wall/gravity — push apart along the contact normal by the overlap amount, then bounce along that normal using `botRestitution` (0.60, independently tunable). Without this, bots visually overlapped instead of colliding. Triggers the same squash-on-hit visual as floor/wall contact.

**Squash and stretch.** Derived from impact velocity on contact: `scaleY = 1 - k·impact`, `scaleX = 1/scaleY`, decaying over ~0.25s. No authoring. Originally specified for floor contact only; extended symmetrically to wall contact (compress along the actual impact axis, stretch the other) and now also fires on bot-vs-bot contact.

**Googly eyes — the highest comedy-per-line ratio in the build.** Each pupil is its own spring-mass with position and velocity, pulled toward socket centre and pushed by the parent body's acceleration, clamped to the eye radius. They lag the body and settle a beat late. Shipped early as directed; re-proportioned (not just linearly rescaled) twice as `botRadius` grew from 7 → 10 → 20, to keep the pupil-to-socket ratio reading as "googly" rather than shrinking to a dot.

**Pixel rendering.** Draw to a 160×90 offscreen canvas, blit to the visible one at 8× with `imageSmoothingEnabled = false` and `image-rendering: pixelated` in CSS. Snap all coordinates to a 1-unit grid, quantise rotation to 15° steps. Eight-colour palette, hard shadows, 1px dark outline, no gradients. Render at ~12fps while physics runs at 60 — the stepped, stop-motion feel is a big part of the look. **Extended beyond the original blob-only spec:** any bot can carry an optional `sprite` (PNG, `media/bots/<slug>.png`, auto-loaded and gracefully falling back to the blob if missing) drawn in place of the blob, still rotated/squashed/pixel-snapped identically; the arena background can likewise be a full image (`media/arena.png`) instead of a flat palette fill. All 24 Pro League bots now have generated sprite art, plus a matching arena background — see §8, this was explicitly out of scope at kickoff.

**Runner.** Walks the beat array against a clock, fires impulses at their `t` (via `snapToContact` first, see above), calls `speak(line)`, shows the caption, applies camera shake.

### Must be right from line one

The low-res buffer and pixel snapping. Retrofitting these after building against smooth vector rendering means rewriting the renderer — the one thing that could actually cost you the demo. **(Historical — this was followed correctly; the pixel pipeline was never retrofitted.)**

---

## 5. Timeline

| T+ | Stream A | Stream B | Joint |
|---|---|---|---|
| 0–5 | — | — | **Agree schema. Commit `sample_beats.json`.** |
| 5–25 | History summariser + first prompt loop | Integrator + bot bodies moving | |
| 25–40 | Beat generation validating clean | Eyes, squash, pixel renderer | |
| **40** | | | **MERGE — real beats through the player** |
| 40–55 | TTS wired, prompt tuning for funnier lines | Camera shake, captions, polish | |
| 55–70 | | | **Tuning pass, one laptop** |
| 70–80 | | | Screen recording + demo script |
| 80+ | | | Buffer. Something will break. |

### Why merge at T+40 and not T+55

First contact between two halves always surfaces something — a field name mismatch, impulses 10× too small for your world scale, `t` in milliseconds instead of seconds. Survivable at T+40. Fatal at T+55.

**Historical note:** actual build ran well past this timeline — `WORKLOG.md` runs to T+~140, roughly 3x the original 2h window, covering the provider swaps, sprite pipeline, and the pacing/collision fixes above. §5-7 are kept as-written below since the *process* (merge-then-tune-then-freeze) was followed correctly even though the clock wasn't.

---

## 6. Merge protocol

Run in this order. Do not skip step 1.

**1. Schema validation, before any integration.** Stream A runs generated output through a validator that checks it against `sample_beats.json`'s exact shape. If it doesn't pass, fix the prompt — do not "adapt the player to handle it." The player has one contract.

**2. Magnitude sanity check.** Play generated beats through the player and watch. The classic failure is impulses that look right in JSON but produce either twitching or bots fired through the ceiling. Fix by adjusting the prompt's scale table, not the physics constants — those are Stream B's and are already tuned against the sample.

**3. Timing check.** Does the commentary land on the impact, or a beat late? If TTS lags, fire `speak()` ~150ms *before* the impulse. Human ears forgive early, not late.

**4. Freeze.** After step 3, `sample_beats.json` and the physics constants are locked. Only prompt text and palette change after this point.

### Conflict avoidance

Separate files, one owner each. Nobody edits the other's files. `index.html` is a thin shell that imports all of them — agree its contents at T+5 and touch it only during merge.

---

## 7. Tuning pass (T+55, both on one laptop)

Nobody currently owns *the funny*, and that's what wins. One person drives constants, the other watches and says "more."

Expose these as live-editable values:

- restitution (0.4 brutal → 0.7 slapstick)
- eye spring stiffness and damping
- squash coefficient
- rotation quantisation step
- camera shake decay

Menace and cute are the same code with different easing. Sharp linear motion reads brutal; bounce and overshoot read funny. This pass is worth more than any feature either of you could add instead.

---

## 8. Scope boundaries (updated post-build)

**In (as shipped, exceeds original plan):** two bots, one arena, impulse-driven physics + simple bot-vs-bot circle collision, googly eyes, pixel rendering with optional per-bot sprite art and an arena background image, live commentary + cloud TTS, a working bot picker over all 24 Pro League bots (not just hardcoded), a 21-value live-tunable debug panel.

**Out (still true):** 3D, general hull/polygon collision solving, weapon geometry, multi-round fights, mobile, anything needing `npm install`.

**No longer out — shipped mid-build, by explicit approval:**
- **Sprite art.** Originally "hand-drawn sprite sheets" were ruled out as too slow to produce in the window. What shipped instead is AI-generated sprite art (external image-gen tool, per `image-gen.md`'s brief) for all 24 bots plus a matching arena background — not hand-drawn, and not built by Stream B's own tooling, but visually the same kind of asset the original boundary was trying to avoid promising. Fully optional at the render layer: any bot without art still falls back to the plain colored blob, so this was additive risk, not a replacement for the blob aesthetic.
- **Bot-vs-bot collision**, in the narrow circle-vs-circle sense — see §4. General hull solving remains out.

**Cut order — as it turned out, nothing was actually cut:**
1. TTS — shipped, upgraded to a cloud voice mid-build rather than cut.
2. Live beat generation — shipped and works (with a provider swap, see §3).
3. Bot selector — shipped in full (real 24-bot roster), not hardcoded.

Never cut: the eyes. (True — eyes shipped early and were never at risk.)

---

## 9. Demo — 30 seconds

1. **The finding.** The results everyone came here to scrape don't exist yet — spoiler ban, episodes still airing. So we dramatise fights that haven't happened, using eight seasons of history.
2. **Play it.** The watch-party matchup, model's call on screen. Fight now runs 70-130s (not 30-45s), so budget the demo slot accordingly — either let it play longer or cut in partway.
3. **The close.** If the model got the fight right, say so. That's the line.

Judges are engineers. The pivot is the story; the cartoon is the payload.

---

## 10. After tonight — now the live roadmap

This section was originally a forward-looking wishlist; the hackathon is done, so this is now where active planning happens. Original ideas kept below as a starting point — see conversation/WORKLOG for what's actually been decided since.

Global `#battlebotsdev` deadline was 31 July. Original obvious-additions list: all 36 group-stage fights pre-rendered as a browsable season, prediction accuracy scored against episodes as they air, YouTube comment sentiment driving crowd-reaction lines.

**Open threads carried over from the build that any roadmap should account for:**
- No true zero-network fallback exists anymore (§1, criterion 1) — worth deciding whether that matters for any future public/offline use.
- Fight duration (70-130s) is now decoupled from the original 45s target — worth deciding if that's the permanent shape or if a shorter TTS-friendly voice/pacing is worth chasing.
- 11 of 24 bot sprites were generated in a batch that skipped the raw-backup step the first 13 got (`sprites/pixel/`) — no functional issue today, just less reprocessable if the chroma-key ever needs revisiting.
- One user-reported physics complaint ("doesn't match the description") was never resolved — no concrete repro was ever given.
