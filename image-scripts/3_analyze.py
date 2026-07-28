#!/usr/bin/env python3
"""
Step 3: Consolidate. Normalise fight rows -> Elo ratings -> weapon meta ->
predictions for the 2026 Pro League fight card that hasn't aired yet.

The 2026 results are mostly NOT public (the wiki bans spoilers, episodes drop
weekly). That's the whole angle: you have the FIGHT CARD but not the outcomes,
plus ~8 seasons of history for these same bots. So you're not ranking a season
that already happened — you're forecasting one that's still airing, and you can
score yourself against the episodes already out.

Usage:
    python3 3_analyze.py

Output: data/rankings.json, data/predictions.json, out/report.html
"""

import json
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

DATA = Path("data")
OUT = Path("out")
OUT.mkdir(exist_ok=True)

bots = json.loads((DATA / "bots.json").read_text())
raw_fights = json.loads((DATA / "fights.json").read_text())
groups = json.loads((Path("raw") / "groups.json").read_text())
NAMES = list(bots)

# The 2026 group-stage card, straight off the Pro League page.
CARD_2026 = [
    ("Manta", "Terrortops"), ("Skorpios", "Valkyrie"), ("Terrortops", "Valkyrie"),
    ("Manta", "Skorpios"), ("Skorpios", "Terrortops"), ("Valkyrie", "Manta"),
    ("Disarray", "MadCatter"), ("Magnitude", "Tombstone"), ("MadCatter", "Magnitude"),
    ("Tombstone", "MadCatter"), ("Tombstone", "Disarray"), ("Disarray", "Magnitude"),
    ("Cobalt", "Copperhead"), ("The Twins", "JackPot"), ("Copperhead", "The Twins"),
    ("JackPot", "Copperhead"), ("The Twins", "Cobalt"), ("Cobalt", "JackPot"),
    ("DeathRoll", "End Game"), ("End Game", "Malice"), ("Golden Fury", "DeathRoll"),
    ("End Game", "Golden Fury"), ("Malice", "Golden Fury"), ("DeathRoll", "Malice"),
    ("Bloodsport", "HUGE"), ("HyperShock", "Bloodsport"), ("HyperShock", "Minotaur"),
    ("HUGE", "Minotaur"), ("HUGE", "HyperShock"), ("Minotaur", "Bloodsport"),
    ("Witch Doctor", "Ribbot"), ("Switchback", "Witch Doctor"), ("Ribbot", "Switchback"),
    ("Orbitron", "Ribbot"), ("Switchback", "Orbitron"), ("Witch Doctor", "Orbitron"),
]

WIN = re.compile(r"\b(win|won|victory)\b", re.I)
LOSS = re.compile(r"\b(loss|lost|defeat)\b", re.I)
KO = re.compile(r"\b(ko|knockout)\b", re.I)

# ------------------------------------------------------- normalise fight rows


def normalise(row: dict) -> dict | None:
    """
    Turn a raw ['World Championship VII','Tombstone','Win','KO'] row into
    {bot, opponent, won, method}. Heuristic: find a cell that names another
    Pro League bot, and a cell that says win/loss.
    """
    cells = row["cells"]
    joined = " | ".join(cells)

    opponent = next(
        (n for n in NAMES if n != row["bot"] and re.search(rf"\b{re.escape(n)}\b", joined, re.I)),
        None,
    )
    if not opponent:
        return None

    if WIN.search(joined) and not LOSS.search(joined):
        won = True
    elif LOSS.search(joined) and not WIN.search(joined):
        won = False
    else:
        return None

    return {
        "bot": row["bot"],
        "opponent": opponent,
        "won": won,
        "ko": bool(KO.search(joined)),
        "raw": joined,
    }


fights = [f for f in (normalise(r) for r in raw_fights) if f]

# de-duplicate: each bout appears on both bots' pages
seen, clean_fights = set(), []
for f in fights:
    key = tuple(sorted([f["bot"], f["opponent"]])) + (f["raw"][:40],)
    if key in seen:
        continue
    seen.add(key)
    clean_fights.append(f)

print(f"Normalised {len(clean_fights)} head-to-head bouts from {len(raw_fights)} raw rows")

# ------------------------------------------------------- Elo

K = 32
elo = {n: 1500.0 for n in NAMES}
history = defaultdict(list)
record = defaultdict(lambda: {"w": 0, "l": 0, "ko_for": 0, "ko_against": 0})

for f in clean_fights:
    a, b = f["bot"], f["opponent"]
    ea = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400))
    sa = 1.0 if f["won"] else 0.0
    elo[a] += K * (sa - ea)
    elo[b] += K * ((1 - sa) - (1 - ea))

    record[a]["w" if f["won"] else "l"] += 1
    record[b]["l" if f["won"] else "w"] += 1
    if f["ko"]:
        record[a]["ko_for" if f["won"] else "ko_against"] += 1
        record[b]["ko_against" if f["won"] else "ko_for"] += 1

    history[a].append(round(elo[a], 1))
    history[b].append(round(elo[b], 1))

rankings = sorted(
    (
        {
            "bot": n,
            "elo": round(elo[n], 1),
            "group": bots[n]["group"],
            "weapon": bots[n].get("weapon", "") or "unknown",
            "wins": record[n]["w"],
            "losses": record[n]["l"],
            "kos_for": record[n]["ko_for"],
            "trajectory": history[n],
        }
        for n in NAMES
    ),
    key=lambda r: -r["elo"],
)

(DATA / "rankings.json").write_text(json.dumps(rankings, indent=2))

# ------------------------------------------------------- weapon meta

weapon_of = {n: (bots[n].get("weapon") or "unknown").lower() for n in NAMES}


def bucket(w: str) -> str:
    for key, label in [
        ("vertical", "vertical spinner"), ("horizontal", "horizontal spinner"),
        ("drum", "drum spinner"), ("undercut", "undercutter"), ("flip", "flipper"),
        ("crush", "crusher"), ("hammer", "hammer"), ("saw", "saw"),
        ("lift", "lifter"), ("axe", "axe"), ("spinner", "spinner"), ("wedge", "wedge"),
    ]:
        if key in w:
            return label
    return "other"


meta = defaultdict(lambda: {"w": 0, "l": 0})
matchup = defaultdict(lambda: {"w": 0, "l": 0})
for f in clean_fights:
    wa, wb = bucket(weapon_of[f["bot"]]), bucket(weapon_of[f["opponent"]])
    meta[wa]["w" if f["won"] else "l"] += 1
    meta[wb]["l" if f["won"] else "w"] += 1
    matchup[(wa, wb)]["w" if f["won"] else "l"] += 1

weapon_meta = sorted(
    (
        {"weapon": k, "wins": v["w"], "losses": v["l"],
         "win_rate": round(v["w"] / max(1, v["w"] + v["l"]), 3)}
        for k, v in meta.items()
    ),
    key=lambda x: -x["win_rate"],
)

# ------------------------------------------------------- predict 2026

predictions = []
for a, b in CARD_2026:
    if a not in elo or b not in elo:
        continue
    p = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400))
    predictions.append({
        "a": a, "b": b,
        "favourite": a if p >= 0.5 else b,
        "p_a_wins": round(p, 3),
        "confidence": round(abs(p - 0.5) * 2, 3),
        "a_elo": round(elo[a], 1), "b_elo": round(elo[b], 1),
    })

(DATA / "predictions.json").write_text(json.dumps(predictions, indent=2))

# every possible matchup — the "infinite bracket" number
all_pairs = [
    {"a": a, "b": b, "p_a_wins": round(1 / (1 + 10 ** ((elo[b] - elo[a]) / 400)), 3)}
    for a, b in combinations(NAMES, 2)
]
(DATA / "all_matchups.json").write_text(json.dumps(all_pairs, indent=2))

# ------------------------------------------------------- report

rows = "".join(
    f"<tr><td>{i+1}</td><td><b>{r['bot']}</b></td><td>{r['group']}</td>"
    f"<td>{r['weapon'][:38]}</td><td>{r['elo']}</td>"
    f"<td>{r['wins']}-{r['losses']}</td><td>{r['kos_for']}</td></tr>"
    for i, r in enumerate(rankings)
)
preds = "".join(
    f"<tr><td>{p['a']} vs {p['b']}</td><td><b>{p['favourite']}</b></td>"
    f"<td>{int(max(p['p_a_wins'], 1-p['p_a_wins'])*100)}%</td></tr>"
    for p in sorted(predictions, key=lambda x: -x["confidence"])
)
wm = "".join(
    f"<tr><td>{w['weapon']}</td><td>{w['wins']}-{w['losses']}</td>"
    f"<td>{int(w['win_rate']*100)}%</td></tr>"
    for w in weapon_meta
)

(OUT / "report.html").write_text(f"""<!doctype html><meta charset=utf-8>
<title>Pro League Priors</title>
<style>
 body{{background:#0d0d0f;color:#e8e8ea;font:15px/1.5 ui-monospace,monospace;
       max-width:900px;margin:40px auto;padding:0 20px}}
 h1{{font-size:28px;letter-spacing:-.5px}} h2{{margin-top:44px;color:#ff5a36}}
 table{{width:100%;border-collapse:collapse;margin-top:14px}}
 td,th{{padding:7px 10px;border-bottom:1px solid #26262b;text-align:left}}
 th{{color:#8a8a94;font-weight:400;font-size:12px;text-transform:uppercase}}
 tr:hover{{background:#17171b}} .n{{color:#8a8a94}}
</style>
<h1>Pro League 2026 — Historical Priors</h1>
<p class=n>Elo built from {len(clean_fights)} prior bouts between the 24 Pro League
competitors. The 2026 season is still airing, so these are forecasts, not results.</p>

<h2>Power rankings</h2>
<table><tr><th>#</th><th>Bot</th><th>Grp</th><th>Weapon</th><th>Elo</th><th>Hist</th><th>KOs</th></tr>
{rows}</table>

<h2>2026 card — model calls</h2>
<table><tr><th>Fight</th><th>Pick</th><th>Confidence</th></tr>{preds}</table>

<h2>Weapon meta</h2>
<table><tr><th>Class</th><th>Record</th><th>Win rate</th></tr>{wm}</table>
""")

print(f"\nTop 5 by Elo:")
for r in rankings[:5]:
    print(f"  {r['elo']:>7.1f}  {r['bot']:<15} {r['wins']}-{r['losses']}")
print(f"\nWrote data/rankings.json, data/predictions.json, out/report.html")
