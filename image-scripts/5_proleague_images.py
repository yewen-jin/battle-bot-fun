#!/usr/bin/env python3
"""
Step 5: Scrape every image + surrounding metadata from the Pro League page.

Source: https://battlebots.com/proleague/
Fetched through Bright Data Web Unlocker (same pattern as 1_scrape.py / 4_images.py)
so it counts for the hack and survives whatever anti-bot the live site has.

For each <img> tag, capture:
  - image_url   (resolved absolute URL; prefers data-src/data-lazy-src/data-original
                 over src, since many sites lazy-load and src is just a placeholder)
  - alt         (alt attribute)
  - title       (title attribute)
  - caption     (nearest <figcaption>, or a sibling/parent with a "caption"-ish class)
  - nearby_heading  (closest preceding h1-h4, for context on what section it's in)
  - page_url    (the page it was found on)

Usage:
    export BRIGHTDATA_API_KEY=...        # or rely on .env (python-dotenv)
    export BRIGHTDATA_UNLOCKER_ZONE=...  # optional, falls back to BRIGHTDATA_ZONE / web_unlocker1
    python3 5_proleague_images.py

Output: raw/proleague_images.csv, raw/proleague_images.json  (one row/object per image)
"""

import csv
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("BRIGHTDATA_API_KEY")
ZONE = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE") or os.environ.get("BRIGHTDATA_ZONE", "web_unlocker1")

if not API_KEY:
    sys.exit("Set BRIGHTDATA_API_KEY first (.env or exported in your shell)")

PAGE_URL = "https://battlebots.com/proleague/"
OUT = Path("raw")
OUT.mkdir(exist_ok=True)

HEADING_TAGS = ("h1", "h2", "h3", "h4")
LAZY_SRC_ATTRS = ("data-src", "data-lazy-src", "data-original", "data-srcset")
# Analytics/tracking pixels, not real content images
TRACKING_DOMAINS = ("facebook.com/tr", "google-analytics.com", "doubleclick.net", "googletagmanager.com")


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


def find_caption(img) -> str:
    """Nearest <figcaption>, else a sibling/parent element that smells like a caption."""
    figure = img.find_parent("figure")
    if figure:
        figcaption = figure.find("figcaption")
        if figcaption:
            return figcaption.get_text(" ", strip=True)

    for sibling in img.find_next_siblings(limit=3):
        cls = " ".join(sibling.get("class", [])).lower()
        if "caption" in cls:
            return sibling.get_text(" ", strip=True)

    parent = img.parent
    if parent:
        cls = " ".join(parent.get("class", [])).lower()
        if "caption" in cls:
            return parent.get_text(" ", strip=True)

    return ""


def find_nearby_heading(img) -> str:
    """Closest preceding heading (h1-h4) in document order, for section context."""
    for el in img.find_all_previous(HEADING_TAGS, limit=1):
        return el.get_text(" ", strip=True)
    return ""


def resolve_src(img, page_url: str) -> str:
    for attr in LAZY_SRC_ATTRS:
        val = img.get(attr)
        if val:
            # data-srcset / srcset-style values are comma-separated "url size" pairs — take the first URL
            first = val.split(",")[0].strip().split(" ")[0]
            if first:
                return urljoin(page_url, first)
    src = img.get("src") or ""
    return urljoin(page_url, src) if src else ""


def scrape_page(page_url: str) -> list[dict]:
    html = unlock(page_url)
    soup = BeautifulSoup(html, "lxml")

    rows = []
    seen = set()
    for img in soup.find_all("img"):
        image_url = resolve_src(img, page_url)
        if not image_url or image_url in seen:
            continue
        if any(d in image_url for d in TRACKING_DOMAINS):
            continue
        seen.add(image_url)
        rows.append(
            {
                "image_url": image_url,
                "alt": img.get("alt", "").strip(),
                "title": img.get("title", "").strip(),
                "caption": find_caption(img),
                "nearby_heading": find_nearby_heading(img),
                "page_url": page_url,
            }
        )
    return rows


if __name__ == "__main__":
    print(f"Fetching {PAGE_URL} via zone '{ZONE}'...")
    rows = scrape_page(PAGE_URL)

    csv_path = OUT / "proleague_images.csv"
    json_path = OUT / "proleague_images.json"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image_url", "alt", "title", "caption", "nearby_heading", "page_url"])
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))

    print(f"\n{'='*60}")
    print(f"Found {len(rows)} images -> {csv_path}, {json_path}")
    if not rows:
        print("No <img> tags found — the page may be rendering images client-side after")
        print("load rather than in the initial HTML. Inspect raw/ output or re-check with")
        print("browser devtools (Network > Img) to see if the real URLs load a different way.")
