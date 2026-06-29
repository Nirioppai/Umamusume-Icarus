#!/usr/bin/env python3
"""
extract_card_art.py  —  Pull the per-trainee STANDING illustration (chara_stand)
from the locally-installed Umamusume (Steam/Global) game assets into
data/card_art/<chara_id>.png, for the v3 UI's full card art + PNG portrait.

Reuses the exact decrypt pipeline from extract_game_icons.py (meta = SQLite3MC
ChaCha20; dat bundles = UnityFS XOR-masked from byte 256 with a per-file FKey;
un-masked bytes -> UnityPy -> Texture2D -> PNG).

What it pulls:
  * chara/chr{chara4}/chara_stand_{chara4}_{variant6}  — 512x512 RGBA standing art.
    There is NO 2048x2048 flat "card art" on disk (the full illustration is rendered
    from the 3D model); 512x512 chara_stand is the real flat-art ceiling.
  * Output keyed by CARD_ID so each card shows ITS OWN outfit (the SIGNATURE RACE
    outfit for base cards + the alt outfit for alt cards). The variant that matches
    a card is chara_stand_{chara4}_{card_id} (verified: 100101<->card 100101,
    100102<->card 100102). Fallback chain per card_id:
      1. chara_stand_{chara4}_{card_id}      (this card's own outfit)
      2. chara_stand_{chara4}_{chara4}01     (the chara's signature/base outfit)
      3. chara_stand_{chara4}_000101 / 000001 (generic school uniform — last resort)

Mapping: the bot keys everything by card_id (6-digit). The serving endpoint
(/api/card-art/<card_id>.png) serves data/card_art/<card_id>.png, falling back to
the chara's base card (xxxx01) then the small portrait icon.

Requires (one-time):  pip install apsw-sqlite3mc UnityPy pillow
Dev-only tool; do NOT ship the from-game pipeline in beta/public builds (the
extracted PNGs ship; this script just won't run without the game install).
"""
from __future__ import annotations
import argparse
import json
import os
import sys

# reuse the proven primitives from the icon extractor (same folder)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_game_icons import open_meta, extract_texture, DEFAULT_GAME  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def card_ids_from_profiles():
    """All distinct card_ids (6-digit) in data/trainee_profiles_core.json."""
    path = os.path.join(REPO, "data", "trainee_profiles_core.json")
    rows = json.loads(open(path, encoding="utf-8").read())
    ids = {int(r["card_id"]) for r in rows if r.get("card_id")}
    return sorted(ids)


def pick_stand_name(card_id: int, by_name: dict):
    """Choose the chara_stand asset name for a card_id (its own outfit first)."""
    chara = f"{card_id // 100:04d}"
    prefix = f"chara/chr{chara}/chara_stand_{chara}_"
    for variant in (
        f"{card_id:06d}",   # this card's own outfit (alt outfit for alt cards)
        f"{chara}01",       # the chara's signature/base outfit
        "000101",           # generic poses (last resort)
        "000001",
    ):
        name = prefix + variant
        if name in by_name:
            return name
    # any card-specific variant (starts with the chara id) over a generic one
    specific = sorted(n for n in by_name if n.startswith(prefix + chara))
    if specific:
        return specific[0]
    cands = sorted(n for n in by_name if n.startswith(prefix))
    return cands[0] if cands else None


def main():
    ap = argparse.ArgumentParser(description="Extract Umamusume standing art into data/card_art")
    ap.add_argument("--game", default=DEFAULT_GAME, help="game install dir (contains meta + dat/)")
    ap.add_argument("--out", default=os.path.join(REPO, "data", "card_art"),
                    help="output dir (default: <repo>/data/card_art)")
    ap.add_argument("--only", default=None, help="comma-separated card_ids to do (debug)")
    ap.add_argument("--dry-run", action="store_true", help="report mapping only; write nothing")
    args = ap.parse_args()

    card_ids = ([int(s) for s in args.only.split(",")] if args.only else card_ids_from_profiles())
    print(f"{len(card_ids)} cards to extract standing art for")

    con = open_meta(args.game)
    rows = con.execute("SELECT n,h,e FROM a").fetchall()
    by_name = {n: (h, e) for (n, h, e) in rows}
    print(f"meta loaded: {len(by_name)} assets")

    if not args.dry_run:
        os.makedirs(args.out, exist_ok=True)

    ok = miss = fail = exact = 0
    misses = []
    for card_id in card_ids:
        name = pick_stand_name(card_id, by_name)
        if not name:
            miss += 1
            misses.append(card_id)
            continue
        if name.endswith(f"_{card_id:06d}"):
            exact += 1
        if args.dry_run:
            ok += 1
            continue
        h, e = by_name[name]
        try:
            img = extract_texture(args.game, h, e)
            if img is None:
                fail += 1
                continue
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            img.save(os.path.join(args.out, f"{card_id}.png"))
            ok += 1
        except Exception as ex:  # noqa: BLE001
            fail += 1
            print(f"  FAIL {card_id} ({name}): {ex}")
        if ok and ok % 25 == 0:
            print(f"  ...{ok} done")

    print(f"\nDONE: {ok} extracted ({exact} exact-card-outfit), {miss} unmapped, {fail} failed (of {len(card_ids)})")
    if misses:
        print("unmapped card_ids:", ", ".join(map(str, misses[:40])) + (" ..." if len(misses) > 40 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
