"""
Stream: data scraping (Bright Data) -> data/bots.json, data/fights.json, raw/groups.json

Two source passes:
  1. Roster pass  - the 24-bot 2026 Pro League card (matchups only, no results - spoiler-banned)
  2. History pass - each bot's fight record across prior seasons (one page per bot on RCE)

Run: python 1_scrape.py
"""

import json
import os
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BRIGHTDATA_API_KEY = os.environ["BRIGHTDATA_API_KEY"]
BRIGHTDATA_ZONE = os.environ.get("BRIGHTDATA_ZONE", "web_unlocker1")
BRIGHTDATA_ENDPOINT = "https://api.brightdata.com/request"

ROSTER_URL = "https://battlebots.fandom.com/wiki/BattleBots_Pro_League"

# TODO: fill once roster is scraped - canonical bot names as they appear on RCE
BOTS = []

# TODO: confirm RCE's URL pattern for a bot's profile/history page
RCE_BOT_URL_TEMPLATE = "https://robotcombatevents.com/robots/{slug}"


def brightdata_get(url: str, render: bool = True) -> str:
    """Fetch a URL through Bright Data's Web Unlocker and return raw HTML."""
    resp = requests.post(
        BRIGHTDATA_ENDPOINT,
        headers={
            "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "zone": BRIGHTDATA_ZONE,
            "url": url,
            "format": "raw",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def slugify(bot_name: str) -> str:
    return bot_name.strip().lower().replace(" ", "-")


def scrape_roster() -> dict:
    """Parse the Pro League page: 24 bots in 6 group tables, plus episode matchups.

    Group standings tables are `.mw-collapsible` under "Group A".."Group F" headings;
    matchup tables are `.article-table` under episode headings. Records/positions are
    deliberately dropped (spoiler ban) - only names, groups, and matchups are kept.
    """
    import re

    html = brightdata_get(ROSTER_URL)
    soup = BeautifulSoup(html, "lxml")
    content = soup.select_one(".mw-parser-output")

    groups = {}
    matchups = []
    for table in content.select("table"):
        cls = table.get("class") or []
        heading = table.find_previous(["h2", "h3", "h4"])
        hname = heading.get_text(strip=True).replace("[]", "").strip() if heading else ""
        if "mw-collapsible" in cls and re.match(r"^Group [A-F]$", hname):
            groups[hname] = [
                row.select("td")[1].get_text(strip=True)
                for row in table.select("tr")
                if len(row.select("td")) >= 2
            ]
        elif "article-table" in cls:
            for row in table.select("tr"):
                text = row.get_text(" ", strip=True)
                if "TBC" in text or "vs" not in text:
                    continue
                parts = text.split("vs.")
                if len(parts) == 2:
                    matchups.append(
                        {"episode": hname or None, "bot_a": parts[0].strip(), "bot_b": parts[1].strip()}
                    )

    bots = sorted({b for bs in groups.values() for b in bs})
    return {"season": 2026, "groups": groups, "bots": bots, "matchups": matchups}


def scrape_bot_specs(bot_name: str) -> dict:
    """Weight class / team / weapon type for one bot, from the Fandom wiki page."""
    url = f"https://battlebots.fandom.com/wiki/{bot_name.replace(' ', '_')}"
    html = brightdata_get(url)
    soup = BeautifulSoup(html, "lxml")

    # TODO: real selectors against the infobox
    return {
        "name": bot_name,
        "weight_class": None,  # TODO
        "team": None,  # TODO
        "weapon_type": None,  # TODO
    }


def scrape_bot_history(bot_name: str) -> list[dict]:
    """Full fight history table for one bot, from its RCE profile page."""
    url = RCE_BOT_URL_TEMPLATE.format(slug=slugify(bot_name))
    html = brightdata_get(url)
    soup = BeautifulSoup(html, "lxml")

    fights = []
    # TODO: real selector for the fight-history table rows
    for row in soup.select("TODO-selector-for-fight-rows"):
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if not cells:
            continue
        # TODO: map cells -> fields once column order is confirmed
        fights.append(
            {
                "event": None,
                "season": None,
                "bot_a": bot_name,
                "bot_b": None,
                "winner": None,
                "method": None,
                "time": None,
                "summary": None,
            }
        )
    return fights


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
    print(f"Fetching roster ({ROSTER_URL})...")
    roster = scrape_roster()
    os.makedirs("raw", exist_ok=True)
    with open("raw/groups.json", "w") as f:
        json.dump(roster, f, indent=2)
    print(f"  -> {len(roster['bots'])} bots -> raw/groups.json")

    bots_out = []
    fights_out = []

    for i, bot_name in enumerate(roster["bots"] or BOTS, start=1):
        print(f"[{i}] {bot_name}: specs...")
        specs = scrape_bot_specs(bot_name)
        time.sleep(0.5)  # be polite between requests

        print(f"[{i}] {bot_name}: history...")
        fights = scrape_bot_history(bot_name)
        time.sleep(0.5)

        specs["record"] = build_record(fights, bot_name)
        specs["win_methods"] = build_win_methods(fights, bot_name)
        bots_out.append(specs)
        fights_out.extend(fights)

    os.makedirs("data", exist_ok=True)
    with open("data/bots.json", "w") as f:
        json.dump(bots_out, f, indent=2)
    with open("data/fights.json", "w") as f:
        json.dump(fights_out, f, indent=2)

    print(f"Done: {len(bots_out)} bots, {len(fights_out)} fight records.")
    print("-> data/bots.json, data/fights.json")


if __name__ == "__main__":
    main()
