#!/usr/bin/env python3
"""Generate trainee skill profiles from Game8 character guide pages.

Input:
  data/game8_character_urls.txt

Output:
  data/trainee_skill_profiles.generated.json

Run:
  python tools/game8_character_profile_scraper.py --root .

The parser is deliberately defensive. Game8 page HTML changes often, so this
script extracts visible text and uses several aptitude/growth/skill heuristics.
Manual profiles in data/trainee_skill_profiles.json still override generated
profiles.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

APTITUDE_RANKS = set("SABCDEFG")
RANK_ORDER = {"S": 8, "A": 7, "B": 6, "C": 5, "D": 4, "E": 3, "F": 2, "G": 1}

DISTANCE_LABELS = {
    "Sprint": "sprint",
    "Mile": "mile",
    "Med": "medium",
    "Medium": "medium",
    "Middle": "medium",
    "Long": "long",
}
TRACK_LABELS = {"Turf": "turf", "Dirt": "dirt"}
STYLE_LABELS = {
    "Front": "front",
    "Front Runner": "front",
    "Pace": "pace",
    "Pace Chaser": "pace",
    "Late": "late",
    "Late Surger": "late",
    "End": "end",
    "End Closer": "end",
}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.title = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property") == "og:title":
            self.title = attrs.get("content", "") or self.title
        if tag == "title":
            self.parts.append("\n")
        if tag in {"br", "p", "tr", "li", "h1", "h2", "h3", "h4", "th", "td", "div"}:
            self.parts.append("\n")

    def handle_data(self, data):
        data = re.sub(r"\s+", " ", data or "").strip()
        if data:
            self.parts.append(data)

    def text(self):
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.parts))


def fetch(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 trainee-profile-generator/1.1"})
    with urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="ignore")


def clean_name(title: str, text: str, url: str) -> str:
    raw = title or ""
    if not raw:
        raw = next((line.strip() for line in text.splitlines() if line.strip()), "")
    raw = re.sub(r"\s*\|.*$", "", raw)
    raw = re.sub(r"\s*Guide.*$", "", raw, flags=re.I)
    raw = re.sub(r"\s*Umamusume.*$", "", raw, flags=re.I)
    raw = re.sub(r"\s*Pretty Derby.*$", "", raw, flags=re.I)
    raw = raw.strip(" -:|")
    return raw or f"Game8 Character {url.rstrip('/').split('/')[-1]}"


def find_rank(text: str, label: str) -> str | None:
    # Most pages render label and rank in nearby cells; support same-line and
    # newline-separated variants.
    snippets = []
    for match in re.finditer(re.escape(label), text, flags=re.I):
        snippets.append(text[match.start():match.start() + 180])
    for snippet in snippets:
        patterns = [
            rf"{re.escape(label)}\s*[:：]?\s*([SABCDEFG])\b",
            rf"{re.escape(label)}\s*\n+\s*([SABCDEFG])\b",
            rf"{re.escape(label)}.*?\b([SABCDEFG])\b",
        ]
        for pattern in patterns:
            m = re.search(pattern, snippet, flags=re.I | re.S)
            if m and m.group(1).upper() in APTITUDE_RANKS:
                return m.group(1).upper()
    return None


def best_key(mapping: dict[str, str], default=""):
    if not mapping:
        return default
    return max(mapping, key=lambda k: RANK_ORDER.get(str(mapping.get(k, "G")).upper(), 0))


def ranked_distances(distance_aptitude: dict[str, str]):
    keys = ["sprint", "mile", "medium", "long"]
    ranked = sorted(keys, key=lambda k: RANK_ORDER.get(str(distance_aptitude.get(k, "G")).upper(), 0), reverse=True)
    primary = [k for k in ranked if str(distance_aptitude.get(k, "G")).upper() in {"S", "A", "B"}][:2]
    if not primary:
        primary = [ranked[0]]
    secondary = [k for k in ranked if k not in primary and str(distance_aptitude.get(k, "G")).upper() in {"B", "C"}]
    avoid = [k for k in ranked if str(distance_aptitude.get(k, "G")).upper() in {"E", "F", "G"}]
    return primary, secondary, avoid


def extract_growth(text: str):
    growth = {"speed": 0, "stamina": 0, "power": 0, "guts": 0, "wit": 0}
    aliases = {
        "Speed": "speed", "SPD": "speed",
        "Stamina": "stamina", "STA": "stamina",
        "Power": "power", "POW": "power", "PWR": "power",
        "Guts": "guts", "GUT": "guts",
        "Wit": "wit", "WIT": "wit", "Wisdom": "wit", "Intelligence": "wit",
    }
    for label, key in aliases.items():
        m = re.search(rf"{label}\s*[:：]?\s*\+?\s*(\d{{1,2}})\s*%", text, flags=re.I)
        if m:
            growth[key] = int(m.group(1))
    return growth


def extract_recommended_stats(text: str):
    """Extract the main recommended stats build, excluding Unity Cup and URA blocks."""
    default_stats = {"Speed": 1200, "Stamina": 600, "Power": 1200, "Guts": 600, "Wit": 1200}
    # Look near the first Recommended Stats section only.
    m = re.search(r"Recommended Stats(.*?)(?:Unity Cup|URA|Recommended Skills|How to Build|Best Build|$)", text, flags=re.I | re.S)
    if not m:
        return dict(default_stats), "default"
    chunk = m.group(1)[:1800]
    aliases = {
        "Speed": "Speed", "SPD": "Speed",
        "Stamina": "Stamina", "STA": "Stamina",
        "Power": "Power", "POW": "Power", "PWR": "Power",
        "Guts": "Guts", "GUT": "Guts",
        "Wit": "Wit", "WIT": "Wit", "Wisdom": "Wit", "Intelligence": "Wit",
    }
    stats = {}
    for label, key in aliases.items():
        found = re.search(rf"{label}\s*[:：]?\s*(\d{{3,4}})", chunk, flags=re.I)
        if found:
            stats[key] = int(found.group(1))

    # Some Game8 tables render values in Speed/Stamina/Power/Guts/Wit order.
    if len(stats) < 5:
        nums = [int(n) for n in re.findall(r"\b(\d{3,4})\b", chunk)]
        plausible = [n for n in nums if 300 <= n <= 2000]
        if len(plausible) >= 5:
            stats = dict(zip(["Speed", "Stamina", "Power", "Guts", "Wit"], plausible[:5]))

    if all(k in stats for k in ["Speed", "Stamina", "Power", "Guts", "Wit"]):
        return {k: int(stats[k]) for k in ["Speed", "Stamina", "Power", "Guts", "Wit"]}, "guide"

    return dict(default_stats), "default"


def extract_skills(text: str):
    unique = ""
    m = re.search(r"Unique Skill\s*\n+\s*([^\n]+)", text, flags=re.I)
    if m:
        unique = m.group(1).strip()
    preferred = []
    skill_sections = ["Recommended Skills", "Innate Skills", "Potential Skills", "Career Skills", "Best Skills"]
    for section in skill_sections:
        m = re.search(rf"{section}\s*(.*?)(?:\n[A-Z][A-Za-z ]{{3,35}}\n|$)", text, flags=re.I | re.S)
        if not m:
            continue
        chunk = m.group(1)[:1500]
        for line in chunk.splitlines():
            line = line.strip(" ・•|-")
            if 3 <= len(line) <= 60 and not re.search(r"^(Tier|Effect|Skill|Description)$", line, flags=re.I):
                preferred.append(line)
    if unique:
        preferred.append(unique)
    return unique, list(dict.fromkeys(preferred))[:40]


def extract_profile(url: str, html: str) -> dict:
    parser = TextExtractor()
    parser.feed(html)
    text = parser.text()
    name = clean_name(parser.title, text, url)

    track = {"turf": find_rank(text, "Turf") or "A", "dirt": find_rank(text, "Dirt") or "G"}
    distance = {}
    for label, key in DISTANCE_LABELS.items():
        distance[key] = find_rank(text, label) or distance.get(key) or "C"
    style = {}
    for label, key in STYLE_LABELS.items():
        style[key] = find_rank(text, label) or style.get(key) or "C"

    primary, secondary, avoid = ranked_distances(distance)
    recommended_style = best_key(style, "front")
    unique, preferred_names = extract_skills(text)
    recommended_stats, recommended_stats_source = extract_recommended_stats(text)

    style_label = {
        "front": "Front Runner",
        "pace": "Pace Chaser",
        "late": "Late Surger",
        "end": "End Closer",
    }.get(recommended_style, recommended_style)

    fragments = []
    for d in primary:
        fragments.extend([d.title(), f"{d.title()} Corners", f"{d.title()} Straightaway"])
    if style_label:
        fragments.extend([style_label, f"{style_label} Corners", f"{style_label} Straightaways"])
    fragments.extend(preferred_names)

    avoid_fragments = []
    for s in {"front", "pace", "late", "end"} - {recommended_style}:
        avoid_fragments.append({
            "front": "Front Runner",
            "pace": "Pace Chaser",
            "late": "Late Surger",
            "end": "End Closer",
        }[s])
    for d in avoid:
        avoid_fragments.append(d.title())
    if track.get("dirt") in {"D", "E", "F", "G"}:
        avoid_fragments.append("Dirt")

    return {
        "name": name,
        "source_url": url,
        "profile_source": "game8_scrape",
        "track_aptitude": track,
        "distance_aptitude": distance,
        "style_aptitude": style,
        "growth": extract_growth(text),
        "unique_skill": unique,
        "recommended_style": recommended_style,
        "primary_distances": primary,
        "secondary_distances": secondary,
        "avoid_distances": avoid,
        "preferred_skill_names": preferred_names,
        "preferred_skill_fragments": sorted(set(fragments)),
        "avoid_skill_fragments": sorted(set(avoid_fragments)),
        "recommended_stats": recommended_stats,
        "recommended_stats_source": recommended_stats_source,
        "green_skill_cap": 1,
        "raw_text_excerpt": text[:2500],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=0, help="Optional scrape limit for testing")
    args = parser.parse_args()

    root = Path(args.root)
    url_path = root / "data" / "game8_character_urls.txt"
    out_path = root / "data" / "trainee_skill_profiles.generated.json"

    urls = [u.strip() for u in url_path.read_text(encoding="utf-8").splitlines() if u.strip()]
    if args.limit:
        urls = urls[:args.limit]

    profiles = {}
    errors = []
    for idx, url in enumerate(urls, 1):
        try:
            html = fetch(url)
            profile = extract_profile(url, html)
            profiles[profile["name"]] = profile
            print(f"[{idx}/{len(urls)}] {profile['name']} {profile['distance_aptitude']} {profile['style_aptitude']}")
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            print(f"[{idx}/{len(urls)}] ERROR {url}: {exc}")
        time.sleep(max(0, args.delay))

    profiles.setdefault("__fallback__", {
        "name": "__fallback__",
        "profile_source": "fallback",
        "track_aptitude": {"turf": "A", "dirt": "G"},
        "distance_aptitude": {"sprint": "C", "mile": "C", "medium": "C", "long": "C"},
        "style_aptitude": {"front": "C", "pace": "C", "late": "C", "end": "C"},
        "recommended_style": "front",
        "primary_distances": ["mile", "medium"],
        "secondary_distances": ["sprint", "long"],
        "avoid_distances": [],
        "preferred_skill_fragments": [],
        "avoid_skill_fragments": [],
        "green_skill_cap": 1,
    })

    out_path.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    report = {
        "source_urls": len(urls),
        "profiles_generated": len([k for k in profiles if k != "__fallback__"]),
        "errors": len(errors),
        "generated_names": sorted(k for k in profiles if k != "__fallback__"),
    }
    (root / "data" / "trainee_skill_profiles.report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if errors:
        (root / "data" / "trainee_skill_profiles.errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
    print(f"Wrote {len(profiles)} profiles to {out_path}")
    print(f"Wrote coverage report to {root / 'data' / 'trainee_skill_profiles.report.json'}")


if __name__ == "__main__":
    main()
