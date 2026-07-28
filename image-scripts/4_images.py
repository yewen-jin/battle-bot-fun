#!/usr/bin/env python3
"""
Step 4: Pull one reference photo per Pro League bot.

Uses the MediaWiki pageimages API to get each page's lead image (which on this
wiki is essentially always the bot's main promo shot), then downloads it through
Bright Data. Fandom URLs support inline resizing, so we ask for 512px wide --
big enough for AI Studio, small enough to download 24 of them in under a minute.

Usage:
    export BRIGHTDATA_API_KEY=...
    export BRIGHTDATA_UNLOCKER_ZONE=cli_unlocker
    python3 4_images.py                 # all 24
    python3 4_images.py Tombstone Minotaur   # just these two -- DO THIS FIRST

Output: sprites/source/<Bot>.jpg  +  sprites/manifest.json
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
    sys.exit("Set BRIGHTDATA_API_KEY first")

OUT = Path("sprites/source")
OUT.mkdir(parents=True, exist_ok=True)

groups = json.loads(Path("raw/groups.json").read_text())
ALL_BOTS = [b for g in groups.values() for b in g]

# Optional CLI filter -- start with two, not twenty-four.
wanted = sys.argv[1:] or ALL_BOTS
BOTS = [b for b in ALL_BOTS if b in wanted] or wanted

WIDTH = 512  # Fandom resizes server-side; no point pulling 4MB originals


def unlock(url: str, binary: bool = False, timeout: int = 90):
    """Fetch through Bright Data Web Unlocker."""
    r = requests.post(
        "https://api.brightdata.com/request",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"zone": ZONE, "url": url, "format": "raw"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.content if binary else r.text


def lead_images(titles: list[str]) -> dict[str, str]:
    """Ask MediaWiki for each page's lead image URL. 6 titles per call."""
    found = {}
    for i in range(0, len(titles), 6):
        batch = titles[i : i + 6]
        joined = "|".join(t.replace(" ", "_") for t in batch)
        url = (
            "https://battlebots.fandom.com/api.php"
            "?action=query&prop=pageimages&piprop=original"
            f"&format=json&redirects=1&titles={joined}"
        )
        try:
            data = json.loads(unlock(url))
        except Exception as e:
            print(f"  !! metadata batch failed: {e}")
            continue

        for page in data.get("query", {}).get("pages", {}).values():
            title = page.get("title", "?")
            src = page.get("original", {}).get("source")
            if src:
                found[title] = src
            else:
                print(f"  ?? no lead image for {title}")
        time.sleep(0.4)
    return found


def resized(url: str, width: int = WIDTH) -> str:
    """Fandom static URLs accept an inline scale directive."""
    base = url.split("/revision/")[0]
    return f"{base}/revision/latest/scale-to-width-down/{width}"


if __name__ == "__main__":
    print(f"Finding lead images for {len(BOTS)} bots...\n")
    urls = lead_images(BOTS)

    manifest = {}
    for name, url in urls.items():
        ext = ".png" if ".png" in url.lower() else ".jpg"
        path = OUT / f"{name.replace(' ', '_')}{ext}"
        try:
            path.write_bytes(unlock(resized(url), binary=True))
            manifest[name] = {"source_url": url, "file": str(path)}
            print(f"  ok  {name:<15} -> {path} ({path.stat().st_size//1024} KB)")
        except Exception as e:
            print(f"  !! {name}: {e}")
        time.sleep(0.3)

    Path("sprites/manifest.json").write_text(json.dumps(manifest, indent=2))

    missing = [b for b in BOTS if b not in manifest]
    print(f"\n{'='*60}")
    print(f"Downloaded {len(manifest)}/{len(BOTS)}")
    if missing:
        print(f"Missing: {missing}")
    print("Next: feed sprites/source/*.jpg to AI Studio, save results to sprites/pixel/")
