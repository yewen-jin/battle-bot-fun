# PRD — OOF: The BattleBots Pro League, Re-enacted Badly

**Build window:** ~2h. Demos at 21:00, hard stop.
**Team:** 2 people, working in parallel from minute zero.
**Deliverable:** one `index.html` you can open with a double-click. No build step, no server, no framework.

---

## 1. Product

Pick any two of the 24 Pro League bots. Get a cartoon re-enactment of their fight: two googly-eyed pixel blobs bouncing around an arena, with sports commentary that is factually grounded in eight seasons of real fight records.

The joke is register mismatch. Broadcast-voice commentary, real stats underneath, and what you're watching is two anxious potatoes falling over.

### Why this shape

The event brief promises a scrapeable season of results. It isn't there — the BattleBots wiki carries a standing spoiler ban on Pro League outcomes, and the episodes are still dropping weekly on YouTube. What exists is the 2026 fight card with unknown results, plus deep historical records for the same 24 bots.

So this is not a recap of fights that happened. It's a **dramatisation of fights that haven't aired yet**, built on what the historical record supports. The model says Tombstone takes this one by KO around ninety seconds; the cartoon shows you that, badly.

### Success criteria

1. Opens in a browser and plays a full fight without touching the network.
2. At least one person watching it laughs out loud.
3. The commentary references a real, checkable fact from the bots' histories.
4. Runs in under 45 seconds end to end.

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
| Bot radius | ~7 units |
| Gravity | 420 u/s² |
| Restitution | 0.55 floor, 0.60 walls |

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
- 18–30 beats, total duration 30–45s
- Gap between beats ≥ 0.8s (TTS needs room to speak)
- `line` under 90 characters
- Final beat should have `target` = loser, a massive impulse, and `shake: 1.0`
- Valid bot names only, from `raw/groups.json`

### Committed at T+5

`sample_beats.json` — a hand-written 20-beat fight, schema-valid, never regenerated. Stream B develops against this exclusively. It is also the fallback demo.

---

## 3. Stream A — data to beats

**Owner:** partner. **Files:** `beats.js`, `speak.js`, `prompts/`

Turns real fight history into a beat array, and speaks it.

### Scope

- Load `data/bots.json` and `data/fights.json` (already scraped — see `1_scrape.py`)
- Build a compact fight-history summary for two named bots
- One Anthropic API call → beat array conforming to the schema above
- Validate output: ascending `t`, gaps ≥ 0.8s, magnitudes in range, names valid. On failure, retry once, then fall back to `sample_beats.json`
- `speak(line)` module wrapping `window.speechSynthesis`
- Fallback screen recording at T+80
- 30-second demo script

### Prompt design notes

- Demand JSON only. No preamble, no markdown fences. Strip fences defensively anyway.
- Put the impulse scale table directly in the system prompt.
- Instruct: commentary is straight and serious, the *physics* is the joke. Never wink at the audience.
- Require at least three lines to reference a specific real fight from the supplied history.
- Ask for a slow build — glancing hits early, massive at the end.

### Known gotcha

`speechSynthesis.getVoices()` returns an empty array on first call. Wait for the `voiceschanged` event before selecting a voice. This eats 20 minutes if you don't know it.

---

## 4. Stream B — beats to pixels

**Owner:** you. **Files:** `physics.js`, `render.js`, `runner.js`

Plays a beat array as animated pixel-art physics.

### Scope

**Integrator.** Fixed timestep, 1/60s. Accumulate real elapsed time, step in fixed chunks, clamp the accumulator to 0.25s. Variable `dt` makes springs explode the moment a frame drops or someone tabs away — and that will happen during the demo.

Per bot: `{x, y, vx, vy, angle, av}`. Each step apply gravity, integrate, then clamp against floor and walls with restitution. Ground contact also damps: `vx *= 0.82`, `av *= 0.70`.

**Impulses.** A beat adds directly to `vx/vy/av`. Nothing else drives motion — no keyframes, no tweens on the bodies. All arcs, tumbles and bounces are emergent.

**Squash and stretch.** Derived from impact velocity on contact: `scaleY = 1 - k·impact`, `scaleX = 1/scaleY`, decaying over ~0.25s. No authoring.

**Googly eyes — the highest comedy-per-line ratio in the build.** Each pupil is its own spring-mass with position and velocity, pulled toward socket centre and pushed by the parent body's acceleration, clamped to the eye radius. They lag the body and settle a beat late. Do these early, not last.

**Pixel rendering.** Draw to a 160×90 offscreen canvas, blit to the visible one at 8× with `imageSmoothingEnabled = false` and `image-rendering: pixelated` in CSS. Snap all coordinates to a 1-unit grid, quantise rotation to 15° steps. Eight-colour palette, hard shadows, 1px dark outline, no gradients. Render at ~12fps while physics runs at 60 — the stepped, stop-motion feel is a big part of the look.

**Runner.** Walks the beat array against a clock, fires impulses at their `t`, calls `speak(line)`, shows the caption, applies camera shake.

### Must be right from line one

The low-res buffer and pixel snapping. Retrofitting these after building against smooth vector rendering means rewriting the renderer — the one thing that could actually cost you the demo.

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

## 8. Scope boundaries

**In:** two bots, one arena, impulse-driven physics, googly eyes, pixel rendering, commentary + TTS, any of the 24 matchups.

**Out:** 3D, hull collision solving, hand-drawn sprite sheets, weapon geometry, multi-round fights, mobile, anything needing `npm install`.

**Cut order if behind:**
1. TTS (captions alone still land)
2. Live beat generation (`sample_beats.json` demos identically — no audience can tell)
3. Bot selector (hardcode the watch-party matchup)

Never cut: the eyes.

---

## 9. Demo — 30 seconds

1. **The finding.** The results everyone came here to scrape don't exist yet — spoiler ban, episodes still airing. So we dramatise fights that haven't happened, using eight seasons of history.
2. **Play it.** The watch-party matchup, model's call on screen.
3. **The close.** If the model got the fight right, say so. That's the line.

Judges are engineers. The pivot is the story; the cartoon is the payload.

---

## 10. After tonight

Global `#battlebotsdev` deadline is 31 July — three days. Obvious additions: all 36 group-stage fights pre-rendered as a browsable season, prediction accuracy scored against episodes as they air, YouTube comment sentiment driving crowd-reaction lines.
