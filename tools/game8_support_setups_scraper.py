#!/usr/bin/env python3
"""Generate recommended support-card setups per trainee for the Trackblazer
(MANT) scenario, scraped from Game8 character build guides.

Input:
  data/game8_character_urls.txt   (75 bare archive URLs)
  data/support_cards_core.json    (for name -> card_id resolution)

Output:
  data/trainee_support_setups.json
  data/trainee_support_setups.report.json

Run:
  python tools/game8_support_setups_scraper.py --root .

Approach mirrors tools/game8_character_profile_scraper.py: stdlib urllib only,
a Mozilla User-Agent, an HTMLParser/TextExtractor that linearizes tables, and
regex/line parsing over the linearized text. No third-party libraries.

Game8 layout (linearized) for each trainee build page:

  Recommended Support Cards
  Trackblazer (MANT) Build
  <Setup Label e.g. "Speed-Wit Setup">
    <Card Name>
    <Card Epithet>            (optional)
    Rarity
    : SSR
    Type
    : Speed
    ... repeated 6 times ...
    <NN>% Race Bonus (MLB)    (optional summary)
  Budget Build
    <Setup Label>
    ... cards ...
  Alternate Cards
  Recommended Alternative Support Cards
    Speed
      <Card Name (Epithet)>
      Rarity : SSR
      Type : Speed
    Stamina ...
  Previous Scenario Builds   <-- HARD STOP (older scenarios, ignore)

The parser keys off the repeating "Rarity\n: <r>\nType\n: <t>" card blocks and
the section headers above. It is defensive: pages missing some sections are
handled gracefully.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


RARITY_LABELS = {"R": 1, "SR": 2, "SSR": 3}
RARITY_NUM_TO_LABEL = {1: "R", 2: "SR", 3: "SSR"}

# Section headers (case-insensitive) used to bound the scrape.
TRACKBLAZER_HEADERS = [
    "Trackblazer (MANT) Build",
    "Trackblazer Build",
    "MANT Build",
]
BUDGET_HEADERS = ["Budget Build"]
ALTERNATE_HEADERS = [
    "Recommended Alternative Support Cards",
    "Alternate Cards",
    "Alternative Support Cards",
]
# Anything from here on belongs to older scenarios -> stop.
STOP_HEADERS = [
    "Previous Scenario Builds",
    "Unity Cup Build",
    "URA Build",
    "URA Scenario Build",
    "Aoharu Cup",
    "Grand Live",
    "Grand Masters",
]


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


def fetch(url: str, timeout: int = 25) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 trainee-support-setups-generator/1.0"})
    with urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="ignore")


def clean_name(title: str, text: str, url: str) -> str:
    raw = title or ""
    if not raw:
        raw = next((line.strip() for line in text.splitlines() if line.strip()), "")
    # og:title looks like:
    #   "Seiun Sky (Soiree des Chatons) Build Guide and Character Info | ...|Game8"
    raw = re.split(r"\s*[|｜]", raw)[0]
    raw = re.sub(r"\s*Build Guide.*$", "", raw, flags=re.I)
    raw = re.sub(r"\s*Guide.*$", "", raw, flags=re.I)
    raw = re.sub(r"\s*Umamusume.*$", "", raw, flags=re.I)
    raw = re.sub(r"\s*Pretty Derby.*$", "", raw, flags=re.I)
    raw = raw.strip(" -:|｜")
    return raw or f"Game8 Character {url.rstrip('/').split('/')[-1]}"


# ---------------------------------------------------------------------------
# Card-name -> card_id resolution
# ---------------------------------------------------------------------------

def load_card_index(root: Path):
    """Return a dict: normalized base name -> list of card dicts.

    The same character name maps to multiple cards (R/SR/SSR variants). We keep
    all of them and pick the best match using rarity when available.
    """
    path = root / "data" / "support_cards_core.json"
    index = {}
    if not path.exists():
        return index
    try:
        cards = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return index
    for c in cards:
        name = c.get("name") or ""
        key = norm(name)
        if not key:
            continue
        index.setdefault(key, []).append({
            "card_id": c.get("support_card_id"),
            "name": name,
            "rarity_num": c.get("rarity"),
        })
    return index


def load_trainee_index(root: Path):
    """Return dict: normalized base trainee name -> sorted list of distinct card_ids.

    trainee_profiles_core.json stores base names (no epithet) and multiple
    card_ids per character (different versions). Game8 names carry an epithet we
    cannot map precisely, so we resolve to a card_id only when the base name has
    a single distinct card_id; otherwise we expose the candidate list + a note.
    """
    path = root / "data" / "trainee_profiles_core.json"
    index = {}
    if not path.exists():
        return index
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return index
    for r in rows:
        key = norm(r.get("name") or "")
        if not key:
            continue
        cid = r.get("card_id")
        bucket = index.setdefault(key, set())
        if cid is not None:
            bucket.add(cid)
    return {k: sorted(v) for k, v in index.items()}


def resolve_trainee(trainee_index, game8_name: str):
    """Return (card_id_or_none, candidate_card_ids, note)."""
    # strip epithet "(...)" to get the base character name
    base = re.sub(r"\s*\(.*?\)\s*$", "", game8_name or "").strip()
    cands = trainee_index.get(norm(base)) or []
    if len(cands) == 1:
        return cands[0], cands, None
    if len(cands) > 1:
        return None, cands, (
            "ambiguous trainee card_id: multiple versions share base name; "
            "Game8 epithet not mappable to a specific card_id"
        )
    return None, [], "no matching trainee base name in trainee_profiles_core.json"


def norm(s: str) -> str:
    s = s or ""
    s = s.lower()
    # unify punctuation/diacritic-ish noise so "T.M. Opera O" ~ "tm opera o"
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Game8 sometimes spells names without spaces (e.g. "Matikanefukukitaru").
# norm() already collapses punctuation; also try the de-spaced form.
def resolve_card_id(index, card_name: str, rarity_label: str | None):
    if not card_name:
        return None
    candidates = index.get(norm(card_name))
    if not candidates:
        # try de-spaced match against de-spaced keys
        target = norm(card_name).replace(" ", "")
        for key, lst in index.items():
            if key.replace(" ", "") == target:
                candidates = lst
                break
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]["card_id"]
    # multiple rarities share the name -> use the scraped rarity to disambiguate
    want = RARITY_LABELS.get((rarity_label or "").upper())
    if want is not None:
        for c in candidates:
            if c.get("rarity_num") == want:
                return c["card_id"]
    # fall back to the highest-rarity card with that name
    best = max(candidates, key=lambda c: c.get("rarity_num") or 0)
    return best["card_id"]


# ---------------------------------------------------------------------------
# Section + card parsing over linearized text
# ---------------------------------------------------------------------------

def find_header(lines, headers, start=0):
    """Return index of the first line (>= start) equal to any header."""
    low = [h.lower() for h in headers]
    for i in range(start, len(lines)):
        if lines[i].strip().lower() in low:
            return i
    return -1


def find_header_contains(lines, headers, start=0):
    low = [h.lower() for h in headers]
    for i in range(start, len(lines)):
        ls = lines[i].strip().lower()
        for h in low:
            if ls == h or ls.startswith(h):
                return i
    return -1


def parse_card_blocks(lines, start, end):
    """Parse repeating card blocks between line indices [start, end).

    A block ends at the "Rarity\n: <r>" / "Type\n: <t>" markers. The 1-2 lines
    immediately preceding the Rarity marker (and after the previous block /
    section header) are the card name and optional epithet.

    Returns a list of card dicts: {name, epithet, type, rarity, raw}.
    Also tags each card with the most recent sub-label seen (setup name or the
    alternate type group like "Speed"/"Stamina"), via the caller.
    """
    cards = []
    i = start
    # Collect "pre" lines that are candidate name/epithet until we hit a Rarity.
    pre = []
    while i < end:
        line = lines[i].strip()
        low = line.lower()
        if low == "rarity" or low.startswith("rarity :") or low.startswith("rarity:"):
            # rarity value: either on same line "rarity : ssr" or next non-empty
            rarity = None
            m = re.search(r"rarity\s*[:：]\s*([a-z]+)", low)
            if m:
                rarity = m.group(1).upper()
                j = i + 1
            else:
                j = i + 1
                while j < end and not lines[j].strip():
                    j += 1
                if j < end:
                    mv = re.match(r"[:：]?\s*([A-Za-z]+)", lines[j].strip())
                    if mv:
                        rarity = mv.group(1).upper()
                    j += 1
            # Type marker should follow
            ctype = None
            # advance to "type"
            k = j
            while k < end and lines[k].strip().lower() not in ("type",) and not lines[k].strip().lower().startswith("type"):
                # don't run away too far
                if k - j > 4:
                    break
                k += 1
            if k < end and lines[k].strip().lower().startswith("type"):
                mt = re.search(r"type\s*[:：]\s*([a-z]+)", lines[k].strip().lower())
                if mt:
                    ctype = mt.group(1).capitalize()
                    nxt = k + 1
                else:
                    nxt = k + 1
                    while nxt < end and not lines[nxt].strip():
                        nxt += 1
                    if nxt < end:
                        mv = re.match(r"[:：]?\s*([A-Za-z]+)", lines[nxt].strip())
                        if mv:
                            ctype = mv.group(1).capitalize()
                        nxt += 1
            else:
                nxt = j
            # Build the card from the collected pre-lines.
            name, epithet = _name_from_pre(pre)
            if name:
                cards.append({
                    "name": name,
                    "epithet": epithet,
                    "type": ctype,
                    "rarity": rarity,
                })
            pre = []
            i = nxt
            continue
        # not a rarity marker -> candidate name/epithet line (filtered)
        if line and not _is_noise(line):
            pre.append(line)
            # keep only the last few candidate lines
            if len(pre) > 3:
                pre = pre[-3:]
        else:
            # noise line resets the pre buffer (e.g. a "% Race Bonus" summary)
            pass
        i += 1
    return cards


def _name_from_pre(pre):
    """Given candidate lines before a Rarity marker, return (name, epithet)."""
    pre = [p for p in pre if p and not _is_noise(p)]
    if not pre:
        return None, None
    if len(pre) == 1:
        # "Name (Epithet)" form used in alternate lists
        m = re.match(r"^(.*?)\s*\((.+)\)\s*$", pre[-1])
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return pre[-1], None
    # Two lines: name then epithet (the build-deck form)
    name = pre[-2]
    epithet = pre[-1]
    # If the "name" line itself is "Name (Epithet)" prefer that and drop epithet
    m = re.match(r"^(.*?)\s*\((.+)\)\s*$", pre[-1])
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return name, epithet


NOISE_RE = re.compile(
    r"^(rarity|type|party formation|"
    r"\d+%\s*race bonus|\(mlb\)|\(slb\)|mlb|slb|race bonus.*|"
    r"recommended.*|for support.*|this deck.*|these cards.*|due to.*)",
    re.I,
)


def _is_noise(line: str) -> bool:
    ls = line.strip().lower()
    if not ls:
        return True
    if NOISE_RE.match(ls):
        return True
    if re.fullmatch(r"[:：].*", ls):
        return True
    if re.fullmatch(r"\d+%?", ls):
        return True
    # very long lines are prose, not card names
    if len(line) > 70:
        return True
    return False


SETUP_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z /\-]+ Setup$", re.I)
ALT_GROUP_LABELS = {"speed", "stamina", "power", "guts", "wit", "pal", "friend", "group"}

# v7.6.3: Game8 prints a "<NN>% Race Bonus (MLB)" summary under each setup's
# six cards. Capture it so the dashboard can show the same caption.
RACE_BONUS_RE = re.compile(r"(\d{1,3})\s*%\s*race\s*bonus(?:\s*\(?\s*([A-Za-z0-9]+)\s*\)?)?", re.I)


_LB_TAG_RE = re.compile(r"\b(MLB|SLB|ML[0-4]|SL[0-4])\b", re.I)


def _find_race_bonus(lines, start, end):
    """Return a normalized 'NN% Race Bonus (TAG)' string in [start, end), or None.

    Game8 prints the percent and the limit-break tag (MLB/ML0/...) either on the
    same line or split across the next couple of lines, so we look ahead a bit.
    """
    upper = min(end, len(lines))
    for i in range(start, upper):
        m = RACE_BONUS_RE.search(lines[i])
        if not m:
            continue
        pct = m.group(1)
        tag = (m.group(2) or "").upper()
        if not _LB_TAG_RE.fullmatch(tag or ""):
            tag = ""
            for j in range(i, min(i + 3, upper)):
                tm = _LB_TAG_RE.search(lines[j])
                if tm:
                    tag = tm.group(1).upper()
                    break
        return f"{pct}% Race Bonus" + (f" ({tag})" if tag else "")
    return None


def parse_setups(lines, start, end):
    """Parse one or more labeled setups in [start, end).

    Splits on lines matching "<...> Setup". Cards before the first such label
    (if any) go into an unlabeled setup.
    """
    # find label positions
    labels = []
    for i in range(start, end):
        if SETUP_LABEL_RE.match(lines[i].strip()):
            labels.append(i)
    setups = []
    if not labels:
        cards = parse_card_blocks(lines, start, end)
        if cards:
            setups.append({"label": "Recommended", "cards": cards, "race_bonus": _find_race_bonus(lines, start, end)})
        return setups
    for idx, li in enumerate(labels):
        seg_start = li + 1
        seg_end = labels[idx + 1] if idx + 1 < len(labels) else end
        cards = parse_card_blocks(lines, seg_start, seg_end)
        if cards:
            setups.append({"label": lines[li].strip(), "cards": cards, "race_bonus": _find_race_bonus(lines, seg_start, seg_end)})
    return setups


def parse_alternates(lines, start, end):
    """Parse the alternate-cards section, grouped by type label."""
    # find type-group label lines
    groups = []
    for i in range(start, end):
        ls = lines[i].strip().lower()
        if ls in ALT_GROUP_LABELS:
            groups.append(i)
    alts = []
    if not groups:
        for c in parse_card_blocks(lines, start, end):
            alts.append(c)
        return alts
    for idx, gi in enumerate(groups):
        seg_start = gi + 1
        seg_end = groups[idx + 1] if idx + 1 < len(groups) else end
        group_type = lines[gi].strip().capitalize()
        for c in parse_card_blocks(lines, seg_start, seg_end):
            if not c.get("type"):
                c["type"] = group_type
            alts.append(c)
    return alts


def attach_ids(cards, index):
    for c in cards:
        c["card_id"] = resolve_card_id(index, c["name"], c.get("rarity"))
        # normalize limit_break field (Game8 puts MLB/SLB near deck summary; we
        # don't reliably get per-card LB, so default None unless epithet carries)
        c.setdefault("limit_break", None)
    return cards


def extract_setups(url: str, html: str, index, trainee_index) -> dict:
    parser = TextExtractor()
    parser.feed(html)
    text = parser.text()
    name = clean_name(parser.title, text, url)
    lines = text.split("\n")

    tcard_id, tcands, tnote = resolve_trainee(trainee_index, name)
    result = {
        "card_id": tcard_id,
        "card_id_candidates": tcands,
        "setups": [],
        "budget": None,
        "alternates": [],
        "source_url": url,
        "notes": [],
    }
    if tnote:
        result["notes"].append(tnote)

    # Anchor the recommended-setup region. Most current pages use a
    # "Trackblazer (MANT) Build" sub-header; some put the Trackblazer deck
    # directly under "Recommended Support Cards" with just a "<...> Setup" label
    # (e.g. "Mixed Setup"). Fall back to the "Recommended Support Cards" header
    # in that case. Older trainees show "Unity Cup Build" immediately after that
    # header -- a STOP header -- so the fallback region is correctly empty.
    rec = find_header_contains(lines, ["Recommended Support Cards"])
    tb = find_header_contains(lines, TRACKBLAZER_HEADERS)
    anchor = tb if tb >= 0 else rec
    used_fallback = tb < 0 and rec >= 0

    stop = find_header_contains(lines, STOP_HEADERS, start=anchor + 1 if anchor >= 0 else 0)
    if stop < 0:
        stop = len(lines)

    budget = find_header_contains(lines, BUDGET_HEADERS, start=anchor if anchor >= 0 else 0)
    if budget >= stop:
        budget = -1
    alt = find_header_contains(lines, ALTERNATE_HEADERS, start=anchor if anchor >= 0 else 0)
    if alt >= stop:
        alt = -1

    # --- Trackblazer recommended setups ---
    if anchor >= 0:
        seg_end = min(x for x in [budget, alt, stop] if x >= 0) if any(x >= 0 for x in [budget, alt, stop]) else stop
        setups = parse_setups(lines, anchor + 1, seg_end)
        for s in setups:
            attach_ids(s["cards"], index)
        result["setups"] = setups
        if used_fallback and setups:
            result["notes"].append(
                "setups parsed from 'Recommended Support Cards' (no explicit "
                "'Trackblazer (MANT) Build' sub-header on this page)"
            )
        elif not setups:
            result["notes"].append("no Trackblazer (MANT) build setups found")
    else:
        result["notes"].append("no Trackblazer (MANT) build section found")

    # --- Budget build ---
    if budget >= 0:
        bend_candidates = [x for x in [alt, stop] if x > budget]
        bend = min(bend_candidates) if bend_candidates else stop
        bsetups = parse_setups(lines, budget + 1, bend)
        for s in bsetups:
            attach_ids(s["cards"], index)
        if bsetups:
            # budget is typically a single setup; keep list for safety
            result["budget"] = {
                "label": bsetups[0]["label"],
                "cards": bsetups[0]["cards"],
                "race_bonus": bsetups[0].get("race_bonus"),
                "extra_setups": bsetups[1:] if len(bsetups) > 1 else [],
            }

    # --- Alternates ---
    if alt >= 0:
        aend_candidates = [x for x in [stop] if x > alt]
        aend = min(aend_candidates) if aend_candidates else stop
        alts = parse_alternates(lines, alt + 1, aend)
        attach_ids(alts, index)
        result["alternates"] = alts

    return name, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Project root")
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0, help="Optional scrape limit for testing")
    args = ap.parse_args()

    root = Path(args.root)
    url_path = root / "data" / "game8_character_urls.txt"
    out_path = root / "data" / "trainee_support_setups.json"
    report_path = root / "data" / "trainee_support_setups.report.json"

    index = load_card_index(root)
    trainee_index = load_trainee_index(root)
    urls = [u.strip() for u in url_path.read_text(encoding="utf-8").splitlines() if u.strip()]
    if args.limit:
        urls = urls[:args.limit]

    out = {}
    errors = []
    failed_parse = []
    for idx, url in enumerate(urls, 1):
        try:
            html = fetch(url)
            name, data = extract_setups(url, html, index, trainee_index)
            out[name] = data
            n_setups = len(data["setups"])
            n_budget = 1 if data["budget"] else 0
            n_alt = len(data["alternates"])
            if n_setups == 0 and n_budget == 0 and n_alt == 0:
                failed_parse.append({"url": url, "name": name, "reason": "no sections parsed"})
            print(f"[{idx}/{len(urls)}] {name}: setups={n_setups} budget={n_budget} alternates={n_alt}")
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            print(f"[{idx}/{len(urls)}] ERROR {url}: {exc}")
        time.sleep(max(0, args.delay))

    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    have_setups = [n for n, d in out.items() if d["setups"]]
    have_budget = [n for n, d in out.items() if d["budget"]]
    have_alt = [n for n, d in out.items() if d["alternates"]]
    report = {
        "source_urls": len(urls),
        "trainees_written": len(out),
        "with_setups": len(have_setups),
        "with_budget": len(have_budget),
        "with_alternates": len(have_alt),
        "with_trainee_card_id": len([n for n, d in out.items() if d.get("card_id") is not None]),
        "fetch_errors": errors,
        "failed_parse": failed_parse,
        "empty_trainees": [n for n, d in out.items()
                           if not d["setups"] and not d["budget"] and not d["alternates"]],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(out)} trainees to {out_path}")
    print(f"setups={len(have_setups)} budget={len(have_budget)} alternates={len(have_alt)} "
          f"errors={len(errors)} failed_parse={len(failed_parse)}")


if __name__ == "__main__":
    main()
