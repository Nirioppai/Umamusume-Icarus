#!/usr/bin/env python3
"""Generate trainee_skill_profiles.json from Game8 character pages.

Usage:
  python tools/game8_profile_scraper.py \
    --list-url https://game8.co/games/Umamusume-Pretty-Derby/archives/535926 \
    --out data/trainee_skill_profiles.json

The scraper is intentionally polite and conservative.  It reads the all-character
list for aptitudes and, when character-page URLs are present, can also follow
those pages to collect recommended skill names.  Game8's markup changes often,
so the generated JSON is editable and the bot treats it as hints, not gospel.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

GRADE_RE = re.compile(r"(Turf|Dirt|Sprint|Mile|Medium|Long|Front|Pace|Late|End):\s*([A-GS])", re.I)
STAT_RE = re.compile(r"\b(SPD|STA|PWR|GUT|WIT)\s*\+\s*(\d+)%", re.I)

class LinkTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._buf = []
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._buf = []
    def handle_data(self, data):
        self.text.append(data)
        if self._href is not None:
            self._buf.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            label = " ".join("".join(self._buf).split())
            if label:
                self.links.append((label, self._href))
            self._href = None
            self._buf = []

def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 skill-profile-generator"})
    with urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", "ignore")

def norm_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

def best(mapping, keys):
    order = {"S":8,"A":7,"B":6,"C":5,"D":4,"E":3,"F":2,"G":1}
    return max(keys, key=lambda k: order.get(mapping.get(k, ""), 0))

def profile_from_block(name: str, href: str, block: str) -> dict:
    apt = {k.lower(): v.upper() for k, v in GRADE_RE.findall(block)}
    distances = ["sprint", "mile", "medium", "long"]
    styles = ["front", "pace", "late", "end"]
    primary = best(apt, distances) if any(d in apt for d in distances) else "mile"
    style = best(apt, styles) if any(s in apt for s in styles) else "front"
    secondary = [d for d in distances if d != primary and apt.get(d) in {"A", "B"}]
    avoid = [d for d in distances if apt.get(d) in {"E", "F", "G"}]
    track = "dirt" if apt.get("dirt") in {"A", "B"} and apt.get("turf") not in {"A", "B"} else "turf"
    growth = {k.upper(): int(v) for k, v in STAT_RE.findall(block)}
    return {
        "match_names": [name],
        "source_url": href,
        "aptitudes": apt,
        "growth": growth,
        "running_style": style,
        "primary_distances": [primary],
        "secondary_distances": secondary,
        "avoid_distances": avoid,
        "track": track,
        "preferred_name_fragments": [style, primary, "corner", "straightaway", "acceleration", "lead" if style == "front" else "position"],
        "preferred_skill_names": [],
        "notes": "Generated from Game8 aptitude table. Add recommended skills after reviewing the character page."
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-url", required=True)
    ap.add_argument("--out", default="data/trainee_skill_profiles.json")
    ap.add_argument("--delay", type=float, default=0.8)
    args = ap.parse_args()
    html = fetch(args.list_url)
    parser = LinkTextParser(); parser.feed(html)
    text = "\n".join(parser.text)
    profiles = {}
    for label, href in parser.links:
        if not href or "/archives/" not in href:
            continue
        # Use a nearby text window from the all-character list where Game8 prints aptitudes.
        idx = text.find(label)
        if idx < 0:
            continue
        block = text[idx: idx + 500]
        if not GRADE_RE.search(block):
            continue
        url = urljoin(args.list_url, href)
        profiles[norm_key(label)] = profile_from_block(label, url, block)
        time.sleep(args.delay)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(profiles)} profiles to {out}")

if __name__ == "__main__":
    main()
