#!/usr/bin/env python3
"""
Step 2: Turn raw wikitext into structured data.

Deliberately GENERIC. We don't know the wiki's exact infobox field names or
table layouts, and at a hackathon you do not want to discover that at 20:45.
So: pull every infobox field and every table row, dump them, and print a preview
so you can eyeball the shape in 30 seconds and then tighten the mapping.

Usage:
    python3 2_extract.py            # deterministic parse
    python3 2_extract.py --llm      # additionally normalise messy rows with Claude
                                    # (needs ANTHROPIC_API_KEY)

Output: data/bots.json, data/fights.json
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

RAW = Path("raw")
DATA = Path("data")
DATA.mkdir(exist_ok=True)

pages = json.loads((RAW / "wikitext.json").read_text())
groups = json.loads((RAW / "groups.json").read_text())
BOTS = [b for g in groups.values() for b in g]

# ---------------------------------------------------------------- infoboxes


def parse_infobox(text: str) -> dict:
    """
    Grab the first {{Infobox ...}} template and return its | key = value pairs.
    Handles nested braces by depth-counting, and splits on top-level pipes only.
    """
    m = re.search(r"\{\{\s*Infobox", text, re.I)
    if not m:
        return {}

    depth, i = 0, m.start()
    while i < len(text):
        if text.startswith("{{", i):
            depth += 1
            i += 2
        elif text.startswith("}}", i):
            depth -= 1
            i += 2
            if depth == 0:
                break
        else:
            i += 1
    block = text[m.start() : i]

    # split on pipes that are not inside [[...]], {{...}} or a table
    parts, buf, d, sq = [], "", 0, 0
    for ch in block[2:-2]:
        if ch == "{":
            d += 1
        elif ch == "}":
            d -= 1
        elif ch == "[":
            sq += 1
        elif ch == "]":
            sq -= 1
        if ch == "|" and d == 0 and sq == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)

    out = {}
    for p in parts[1:]:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        out[k.strip().lower()] = clean(v)
    return out


def clean(s: str) -> str:
    """Strip wiki markup down to plain text."""
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<br\s*/?>", ", ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)  # [[Target|Label]] -> Label
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = s.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip(" |\n\t")


# ---------------------------------------------------------------- tables


def parse_tables(text: str) -> list[list[list[str]]]:
    """Return every wikitable as a list of rows, each row a list of cell strings."""
    tables = []
    for raw_table in re.findall(r"\{\|(.*?)\n\|\}", text, re.S):
        rows = []
        for chunk in re.split(r"\n\|-+", raw_table):
            cells = []
            for line in chunk.split("\n"):
                line = line.strip()
                if line.startswith("!") or line.startswith("|"):
                    line = line.lstrip("!|").strip()
                    # inline cell separators
                    for cell in re.split(r"\|\||!!", line):
                        c = clean(cell)
                        if c:
                            cells.append(c)
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


RESULT_WORDS = re.compile(r"\b(win|won|loss|lost|ko|knockout|judges|unanimous|split|draw|tie)\b", re.I)


def looks_like_fights(rows: list[list[str]]) -> bool:
    """A results table is one where a decent share of rows mention win/loss/KO."""
    if len(rows) < 2:
        return False
    hits = sum(1 for r in rows if RESULT_WORDS.search(" ".join(r)))
    return hits >= max(2, len(rows) * 0.3)


# ---------------------------------------------------------------- build

bots, fights = {}, []

for name in BOTS:
    text = pages.get(name)
    if not text:
        print(f"!! no wikitext for {name}")
        continue

    info = parse_infobox(text)
    tables = parse_tables(text)
    fight_tables = [t for t in tables if looks_like_fights(t)]

    bots[name] = {
        "name": name,
        "group": next(g for g, m in groups.items() if name in m),
        "infobox": info,
        # best-effort convenience fields — CHECK THESE against the preview below
        "weapon": info.get("weapon") or info.get("weapon type") or info.get("weapons", ""),
        "weight": info.get("weight", ""),
        "team": info.get("team", "") or info.get("team members", ""),
        "country": info.get("country", "") or info.get("origin", ""),
        "record": info.get("record", "") or info.get("fight record", ""),
        "n_tables": len(tables),
        "n_fight_tables": len(fight_tables),
    }

    for t in fight_tables:
        header = t[0]
        for row in t[1:]:
            fights.append({"bot": name, "header": header, "cells": row})

(DATA / "bots.json").write_text(json.dumps(bots, indent=2, ensure_ascii=False))
(DATA / "fights.json").write_text(json.dumps(fights, indent=2, ensure_ascii=False))

# ---------------------------------------------------------------- diagnostics

print(f"\n{'='*64}")
print(f"Bots parsed:      {len(bots)}/24")
print(f"Raw fight rows:   {len(fights)}")

field_freq = Counter(k for b in bots.values() for k in b["infobox"])
print(f"\nMost common infobox fields (use these as your real schema):")
for k, n in field_freq.most_common(15):
    print(f"  {n:>3}x  {k}")

print(f"\nSample bot record:")
if bots:
    sample = bots[next(iter(bots))]
    print(json.dumps({k: v for k, v in sample.items() if k != "infobox"}, indent=2)[:800])

print(f"\nSample fight rows:")
for f in fights[:5]:
    print(f"  {f['bot']}: {f['cells']}")

empty = [n for n, b in bots.items() if not b["weapon"]]
if empty:
    print(f"\n!! No weapon field resolved for: {empty}")
    print("   Look at the field list above and remap in the 'weapon' line.")

print(f"\nWrote data/bots.json and data/fights.json")
