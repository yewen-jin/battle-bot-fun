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

# TODO: fill from the 2026 Pro League roster/fight-card page (matchups, not outcomes)
ROSTER_URL = "https://battlebots.fandom.com/wiki/2026_Pro_League"  # placeholder, verify

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
    """Parse the 2026 fight-card page: 24 canonical bot names (+ groups if listed)."""
    html = brightdata_get(ROSTER_URL)
    soup = BeautifulSoup(html, "lxml")

    # TODO: real selector once the page HTML is inspected
    bots = []
    for el in soup.select("TODO-selector-for-bot-names"):
        bots.append(el.get_text(strip=True))

    return {"season": 2026, "bots": bots}


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
