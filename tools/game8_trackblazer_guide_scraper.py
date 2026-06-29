
"""Scrape/refresh Trackblazer guide heuristics from Game8.

This is intentionally conservative: it downloads the public guide page and refreshes
a small JSON heuristic file used by the bot. It does not need browser automation.
"""
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://game8.co/games/Umamusume-Pretty-Derby/archives/580723"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "trackblazer_game8_strategy.json"

def fetch(url=URL):
    req = Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="ignore")

def parse(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    data["source"] = URL
    data["scraped_hint"] = "public Game8 Trackblazer guide text parsed into bot heuristics"
    # Keep these stable unless the page wording changes enough to identify new numbers.
    if "at least 25 Races" in text or "at least 25 races" in text:
        data["target_races_min"] = 25
    if "minimum of 50 Race Bonus" in text or "at least 50" in text:
        data["race_bonus_target"] = 50
    if "2 races and 1 free turn" in text:
        data.setdefault("race_pattern", {})["race_chain_target"] = 2
        data["race_pattern"]["free_turn_after_chain"] = 1
    if "Scholar" in text and "280" in text:
        data.setdefault("shop_priorities", {}).setdefault("fast_learner", {})["min_coin_before_buy"] = 280
    return data

def main():
    html = fetch()
    data = parse(html)
    OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
