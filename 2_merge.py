"""
Merge subagent scrape outputs into the final data files.

Inputs:  raw/groups.json, raw/specs.json, raw/histories_a.json, raw/histories_b.json
Outputs: data/bots.json, data/fights.json

Run: python3 2_merge.py
"""

import json
import os


def build_win_methods(fights: list[dict], bot_name: str) -> dict:
    methods = {}
    for f in fights:
        if f.get("winner") == bot_name and f.get("method"):
            methods[f["method"]] = methods.get(f["method"], 0) + 1
    return methods


def build_record(fights: list[dict], bot_name: str) -> dict:
    wins = sum(1 for f in fights if f.get("winner") == bot_name)
    losses = sum(
        1
        for f in fights
        if bot_name in (f.get("bot_a"), f.get("bot_b")) and f.get("winner") not in (None, bot_name)
    )
    return {"wins": wins, "losses": losses, "draws": 0}


def main():
    with open("raw/groups.json") as f:
        roster = json.load(f)
    with open("raw/specs.json") as f:
        specs = json.load(f)

    fights = []
    for part in ("raw/histories_a.json", "raw/histories_b.json"):
        if os.path.exists(part):
            with open(part) as f:
                fights.extend(json.load(f))

    # de-dup fights that appear on both bots' pages (same event + unordered pair)
    seen = set()
    deduped = []
    for f in fights:
        key = (f.get("event"), f.get("season"), frozenset([f.get("bot_a"), f.get("bot_b")]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)

    specs_by_name = {s["name"]: s for s in specs}
    group_by_bot = {b: g for g, bs in roster.get("groups", {}).items() for b in bs}

    bots_out = []
    for name in roster["bots"]:
        bot = specs_by_name.get(name, {"name": name, "weight_class": None, "team": None, "weapon_type": None})
        bot_fights = [f for f in deduped if name in (f.get("bot_a"), f.get("bot_b"))]
        bot["group"] = group_by_bot.get(name)
        bot["record"] = build_record(bot_fights, name)
        bot["win_methods"] = build_win_methods(bot_fights, name)
        bots_out.append(bot)

    os.makedirs("data", exist_ok=True)
    with open("data/bots.json", "w") as f:
        json.dump(bots_out, f, indent=2)
    with open("data/fights.json", "w") as f:
        json.dump(deduped, f, indent=2)

    print(f"{len(bots_out)} bots, {len(deduped)} fights ({len(fights) - len(deduped)} duplicates dropped)")
    missing_specs = [b["name"] for b in bots_out if not b.get("weapon_type")]
    no_fights = [b["name"] for b in bots_out if b["record"]["wins"] + b["record"]["losses"] == 0]
    if missing_specs:
        print("missing weapon_type:", missing_specs)
    if no_fights:
        print("no fight history:", no_fights)


if __name__ == "__main__":
    main()
