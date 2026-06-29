#!/usr/bin/env python3
"""
gametora_event_scraper.py — build data/event_effects.json (the bot's event-choice
database) from gametora.com + the game's master.mdb.

Replaces the old game8 scraper. gametora supplies the per-choice reward STRUCTURE
(stat deltas, skill-hint ids, bond, energy, …) that master.mdb does not store;
master.mdb resolves skill ids -> English names and cross-checks event titles.

How it works:
  1. ENUMERATE every support card + trainee from gametora's sitemap
     (https://gametora.com/sitemap-0.xml -> /umamusume/supports/<id-slug> and
     /umamusume/characters/<id-slug>).
  2. For each page, fetch the HTML and read the embedded
     <script id="__NEXT_DATA__"> JSON -> props.pageProps.eventData.en (a JSON
     string). The buildId-based _next/data route is NOT used (it rotates).
  3. Each event = {i, n(name, English), c:[{o(JP option text), r:[{t,v,d}]}]}.
     Decode each reward token (t) to the canonical "Label +N" effect string the
     bot's career_bot/events.py:_parse_effect_string understands. Skill tokens
     (sk/sg) carry d=skill_id -> resolved to a name via master.mdb text_data
     category 47.
  4. Dedup events by name (common/shared events repeat across trainees), write
     data/event_effects.json keyed by name-slug with the SAME schema the bot
     already consumes, plus data/event_effects.report.json (coverage audit).

Runtime is OFFLINE-FIRST: the bot reads the shipped JSON and never calls gametora.
This is a maintainer tool — run it to refresh the bundled data after a game patch.

Requires: a current master.mdb (game's, or a copy) + network for the scrape.
Usage:  python tools/gametora_event_scraper.py [--mdb PATH] [--limit N] [--offline]
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Icarus event-data maintainer tool)"}
BASE = "https://gametora.com"

# gametora reward token `t` -> canonical label understood by _parse_effect_string.
# (Speed/Stamina/Power/Guts/Wisdom/Energy/Max Energy/Motivation/Skill points/Bond/
#  All stats/Skill hint are the only scoreable labels; everything else is dropped
#  from `effect` but kept in `display`/`raw`.)
REWARD_LABELS = {
    "sp": "Speed", "st": "Stamina", "po": "Power", "gu": "Guts", "in": "Wisdom",
    "en": "Energy", "me": "Max Energy", "mo": "Motivation", "pt": "Skill points",
    "bo": "Bond", "bo_ch": "Bond", "5s": "All stats", "ap": "All stats",
}
SKILL_TOKENS = {"sk", "sg", "se"}          # carry d = skill_id
# Branch dividers: a choice's reward list can encode several CONDITIONAL outcomes
# (by fan count / stat threshold / skill possession) separated by these tokens.
# We score only the FIRST (best-case) branch — summing all branches would massively
# over-value the choice. ('di' = explicit OR, 'nl' = gametora's branch newline.)
BRANCH_DIVIDERS = {"di", "nl"}
# tokens with no scoreable equivalent — omitted from `effect`, kept in `display`/raw.
# Includes condition MARKERS (ct=count, w_e/ps_*/se_*=possession/result gates, rc/rr/
# rs=race/random, no=none, hp/ht/ds/rl/ra/rh/fe/fd/sr/brf/brp/ha/sc/et=misc/scenario).
NONSCORE_KNOWN = {
    "fa", "ee", "he", "lb", "ev", "ce", "gp", "co",
    "ct", "w_e", "ps_h", "ps_nh", "se_h", "se_nh", "rc", "rr", "rs", "no",
    "hp", "ht", "ds", "rl", "ra", "rh", "fe", "fd", "sr", "brf", "brp", "ha", "sc", "et",
}

DEFAULT_MDB_CANDIDATES = [
    os.path.expandvars(r"%LOCALAPPDATA%Low\Cygames\Umamusume\master\master.mdb"),
    os.path.join(os.path.dirname(REPO), "master_check.mdb"),
    os.path.join(REPO, "master.mdb"),
]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def fetch(url: str, timeout: int = 25) -> str:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode("utf-8", "replace")


def next_data(html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("no __NEXT_DATA__")
    return json.loads(m.group(1))["props"]["pageProps"]


# ---------------------------------------------------------------- enumeration
def enumerate_pages():
    sm = fetch(BASE + "/sitemap-0.xml")
    sup = sorted(set(re.findall(r"/umamusume/supports/(\d+-[a-z0-9-]+)", sm)))
    chars = sorted(set(re.findall(r"/umamusume/characters/(\d+-[a-z0-9-]+)", sm)))
    out = [("supports", s) for s in sup] + [("characters", s) for s in chars]
    return out


# ---------------------------------------------------------------- master.mdb
def load_master(path):
    con = sqlite3.connect(path)
    skill = {int(i): t for i, t in con.execute("SELECT \"index\",text FROM text_data WHERE category=47")}
    title_index = defaultdict(list)
    for i, t in con.execute("SELECT \"index\",text FROM text_data WHERE category=181"):
        title_index[norm(t)].append((int(i), t))
    con.close()
    return {"skill": skill, "title_index": title_index}


def skill_name(master, sid):
    try:
        return master["skill"].get(int(sid)) or f"Skill {sid}"
    except Exception:
        return f"Skill {sid}"


# ---------------------------------------------------------------- decode
def decode_choice(rewards, master, unknown_counter):
    """Return (effect, display, raw) for one choice's reward token list."""
    eff, disp, raw = [], [], []
    branch_cut = False   # after an OR-divider, stop adding to the (guaranteed) effect
    for r in rewards or []:
        if not isinstance(r, dict):
            continue
        t = r.get("t")
        v = str(r.get("v") or "").strip()
        d = r.get("d")
        raw.append({k: r[k] for k in ("t", "v", "d") if k in r})
        if t in BRANCH_DIVIDERS:
            branch_cut = True       # score only the first/best-case branch
            disp.append("/ or")
            continue
        if t in SKILL_TOKENS:
            nm = skill_name(master, d) if d is not None else "Skill"
            if t == "sg":
                if not branch_cut:
                    eff.append("Skill hint +1")
                disp.append(f"{nm} (obtained)")
            else:
                hint = v if v and v[0] in "+-" else "+1"
                if not branch_cut:
                    eff.append(f"Skill hint {hint}")
                disp.append(f"{nm} {hint} Skill Hint")
            continue
        if t in REWARD_LABELS:
            lbl = REWARD_LABELS[t]
            if not v:
                continue
            sign = v if v[0] in "+-" else ("+" + v)
            if not branch_cut:
                eff.append(f"{lbl} {sign}")
            disp.append(f"{lbl} {sign}")
            continue
        if t not in NONSCORE_KNOWN:
            unknown_counter[t] += 1   # surface genuinely-new tokens in the report
    return ", ".join(eff), ", ".join(disp), raw


def parse_event_data(pp):
    """pageProps -> list of event dicts from eventData.en (sections vary by page).

    eventData = {ja,ko,zh_tw,en}; eventData['en'] is a JSON STRING whose top level
    is a dict of sections. Section values are usually event LISTS, but some are
    scalars (e.g. 'version') — those are skipped, never re-parsed.
    """
    ed = pp.get("eventData")
    if not isinstance(ed, dict):
        return []
    en = ed.get("en")
    try:
        sections = json.loads(en) if isinstance(en, str) else (en if isinstance(en, dict) else {})
    except Exception:
        return []
    events = []
    for sec_name, sec in (sections.items() if isinstance(sections, dict) else []):
        if not isinstance(sec, list):     # scalar sections (version, …) are not events
            continue
        for order, ev in enumerate(sec):
            if isinstance(ev, dict) and ev.get("n"):
                events.append((sec_name, order, ev))
    return events


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Build data/event_effects.json from gametora + master.mdb")
    ap.add_argument("--mdb", default=None, help="path to master.mdb (default: game install / repo copy)")
    ap.add_argument("--out", default=os.path.join(REPO, "data", "event_effects.json"))
    ap.add_argument("--cache-dir", default=os.path.join(REPO, "tools", ".gametora_cache"))
    ap.add_argument("--limit", type=int, default=0, help="only scrape the first N pages (debug)")
    ap.add_argument("--offline", action="store_true", help="use only cached pages (no network)")
    ap.add_argument("--sleep", type=float, default=0.6, help="seconds between requests")
    args = ap.parse_args()

    mdb = args.mdb or next((p for p in DEFAULT_MDB_CANDIDATES if os.path.exists(p)), None)
    if not mdb or not os.path.exists(mdb):
        print("ERROR: master.mdb not found; pass --mdb PATH", file=sys.stderr)
        return 2
    print(f"master.mdb: {mdb}")
    master = load_master(mdb)
    print(f"  skills: {len(master['skill'])}, event titles: {len(master['title_index'])}")

    os.makedirs(args.cache_dir, exist_ok=True)
    pages = enumerate_pages()
    if args.limit:
        pages = pages[:args.limit]
    print(f"pages to process: {len(pages)} ({sum(1 for k,_ in pages if k=='supports')} supports, {sum(1 for k,_ in pages if k=='characters')} characters)")

    out = {}
    seen_name = {}          # norm(name) -> slug (dedup shared/common events)
    unknown = defaultdict(int)
    counts = defaultdict(int)
    title_hits = 0
    n_pages = fetched = cached = failed = 0

    def slug_for(name):
        base = norm(name) or "event"
        slug = base
        i = 2
        while slug in out:
            slug = f"{base}-{i}"
            i += 1
        return slug

    for kind, idslug in pages:
        n_pages += 1
        cache_path = os.path.join(args.cache_dir, f"{kind}_{idslug}.json")
        pp = None
        if os.path.exists(cache_path):
            try:
                pp = json.loads(open(cache_path, encoding="utf-8").read())
                cached += 1
            except Exception:
                pp = None
        if pp is None:
            if args.offline:
                continue
            url = f"{BASE}/umamusume/{kind}/{idslug}"
            try:
                pp = next_data(fetch(url))
                open(cache_path, "w", encoding="utf-8").write(json.dumps(pp, ensure_ascii=False))
                fetched += 1
                time.sleep(args.sleep)
            except Exception as ex:  # noqa: BLE001
                failed += 1
                print(f"  FAIL {kind}/{idslug}: {ex}")
                continue
        category = "support_card" if kind == "supports" else "story"
        for sec_name, order, ev in parse_event_data(pp):
            name = str(ev.get("n") or "").strip()
            if not name:
                continue
            key = norm(name)
            if key in seen_name:
                continue            # shared/common event already captured
            choices_in = ev.get("c") or []
            choices = {}
            for ci, ch in enumerate(choices_in):
                if not isinstance(ch, dict):
                    continue
                eff, disp, raw = decode_choice(ch.get("r"), master, unknown)
                sel = "0" if len(choices_in) <= 1 else str(ci + 1)
                choices[sel] = {
                    "label": "No Choices" if len(choices_in) <= 1 else f"Choice {ci + 1}",
                    "effect": eff, "display": disp, "raw": raw,
                }
            if not choices:
                continue
            # canonical English title cross-check against master (cat 181)
            cand = master["title_index"].get(key)
            event_name = cand[0][1] if cand else name
            if cand:
                title_hits += 1
            slug = slug_for(event_name)
            seen_name[key] = slug
            out[slug] = {
                "event_name": event_name,
                "category": category,
                "source": "gametora",
                "source_url": f"{BASE}/umamusume/{kind}/{idslug}",
                "fixed": len(choices_in) <= 1,
                "choices": choices,
            }
            counts[category] += 1
        if n_pages % 50 == 0:
            print(f"  ...{n_pages}/{len(pages)} pages, {len(out)} events")

    # validation gate — never overwrite good data with a broken scrape
    if len(out) < 50:
        print(f"ERROR: only {len(out)} events parsed — refusing to write (likely a broken scrape).", file=sys.stderr)
        return 3

    meta = {
        "source": "gametora.com/umamusume + master.mdb (text_data)",
        "generated_by": "tools/gametora_event_scraper.py",
        "note": "Keyed by name slug. event_name (English) drives name-based lookup. "
                "effect strings are canonical 'Label +N' parsed by career_bot/events.py:_parse_effect_string. "
                "Skill ids resolved to names via master.mdb category 47.",
        "counts": {**{k: counts[k] for k in counts}, "total": len(out),
                   "title_matched_master": title_hits},
        "unknown_reward_tokens": dict(unknown),
        "mdb_mtime": int(os.path.getmtime(mdb)),
    }
    payload = {"_meta": meta}
    for k in sorted(out):
        payload[k] = out[k]

    tmp = args.out + ".tmp"
    open(tmp, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2))
    os.replace(tmp, args.out)
    report = {"counts": meta["counts"], "unknown_reward_tokens": dict(unknown),
              "pages": n_pages, "fetched": fetched, "cached": cached, "failed": failed}
    open(os.path.join(REPO, "data", "event_effects.report.json"), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=2))

    print(f"\nDONE: {len(out)} events ({dict(counts)}), title-matched {title_hits}, "
          f"unknown tokens {dict(unknown)}")
    print(f"  pages={n_pages} fetched={fetched} cached={cached} failed={failed}")
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
