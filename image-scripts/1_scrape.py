#!/usr/bin/env python3
"""
Step 1: Pull raw source data for all 24 BattleBots Pro League bots.

Key trick: battlebots.fandom.com is MediaWiki, so it exposes /api.php.
We fetch WIKITEXT, not HTML. Wikitext gives you clean `| weapon = Vertical spinner`
infobox fields and pipe-delimited tables instead of 4,000 lines of Fandom nav soup.

Everything is fetched THROUGH Bright Data Web Unlocker so it counts for the hack
and doesn't get rate-limited when 40 people in the room hit the same wiki.

Usage:
    export BRIGHTDATA_API_KEY=...
    export BRIGHTDATA_UNLOCKER_ZONE=cli_unlocker   # or whatever `bdata zones` shows
    python3 1_scrape.py

Output: raw/wikitext.json  — {page_title: wikitext}
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

API_KEY = os.environ.get("BRIGHTDATA_API_KEY")
ZONE = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "cli_unlocker")

if not API_KEY:
    sys.exit("Set BRIGHTDATA_API_KEY first (run `bdata login` then check `bdata config`)")

OUT = Path("raw")
OUT.mkdir(exist_ok=True)

# The 24 Pro League competitors, by their exact wiki page titles.
# Grouped as drawn for the 2026 season.
GROUPS = {
    "A": ["Manta", "Terrortops", "Skorpios", "Valkyrie"],
    "B": ["Disarray", "MadCatter", "Magnitude", "Tombstone"],
    "C": ["Cobalt", "Copperhead", "The Twins", "JackPot"],
    "D": ["DeathRoll", "End Game", "Golden Fury", "Malice"],
    "E": ["Bloodsport", "HUGE", "HyperShock", "Minotaur"],
    "F": ["Witch Doctor", "Ribbot", "Switchback", "Orbitron"],
}
BOTS = [b for g in GROUPS.values() for b in g]

# Extra context pages worth having in the corpus.
EXTRA = [
    "BattleBots_Pro_League",
    "World_Championship_VII",
    "BattleBots:_Champions_II",
    "BattleBots_FaceOffs",
]


def unlock(url: str, timeout: int = 90) -> str:
    """Fetch a URL through Bright Data Web Unlocker, return the raw body."""
    r = requests.post(
        "https://api.brightdata.com/request",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"zone": ZONE, "url": url, "format": "raw"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text


def fetch_wikitext(titles: list[str]) -> dict[str, str]:
    """
    MediaWiki lets you request up to 50 pages in ONE call.
    24 bots = 4 requests at batch size 6. Keep batches small so a single
    bad title doesn't cost you the whole response.
    """
    pages: dict[str, str] = {}

    for i in range(0, len(titles), 6):
        batch = titles[i : i + 6]
        joined = "|".join(t.replace(" ", "_") for t in batch)
        url = (
            "https://battlebots.fandom.com/api.php"
            "?action=query&prop=revisions&rvprop=content&rvslots=main"
            f"&format=json&redirects=1&titles={joined}"
        )
        print(f"  fetching batch {i//6 + 1}: {', '.join(batch)}")

        try:
            body = unlock(url)
            data = json.loads(body)
        except Exception as e:
            print(f"  !! batch failed ({e}) — retrying once in 3s")
            time.sleep(3)
            try:
                data = json.loads(unlock(url))
            except Exception as e2:
                print(f"  !! batch dead: {e2}. Skipping.")
                continue

        for page in data.get("query", {}).get("pages", {}).values():
            title = page.get("title", "?")
            if "missing" in page:
                print(f"  ?? no such page: {title}")
                continue
            try:
                text = page["revisions"][0]["slots"]["main"]["*"]
            except (KeyError, IndexError):
                print(f"  ?? no revision content for {title}")
                continue
            pages[title] = text
            print(f"  ok  {title}  ({len(text):,} chars)")

        time.sleep(0.5)

    return pages


if __name__ == "__main__":
    print(f"Scraping {len(BOTS)} bots + {len(EXTRA)} context pages via zone '{ZONE}'\n")

    pages = fetch_wikitext(BOTS + EXTRA)

    (OUT / "wikitext.json").write_text(json.dumps(pages, indent=2, ensure_ascii=False))
    (OUT / "groups.json").write_text(json.dumps(GROUPS, indent=2))

    got = [b for b in BOTS if b in pages]
    missing = [b for b in BOTS if b not in pages]

    print(f"\n{'='*60}")
    print(f"Saved {len(pages)} pages to raw/wikitext.json")
    print(f"Bots captured: {len(got)}/24")
    if missing:
        print(f"MISSING (fix the title spelling and re-run): {missing}")
    print("Next: python3 2_extract.py")
