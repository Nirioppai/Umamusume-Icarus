#!/usr/bin/env python3
"""
extract_card_names.py — build data/card_names_core.json: per-card (per card_id)
trainee names that include the costume/version, e.g.
    103601 -> "Air Shakur (unsigned)"
    100101 -> "Special Week (Special Dreamer)"

Source: master.mdb text_data category 4 ("[Title] Name", per card_id). We reorder
that to "Name (Title)" so the v3 trainee picker can show each owned version with
its own version name (and its own per-card_id outfit icon).

master.mdb is plain SQLite. Usage: python tools/extract_card_names.py [--mdb PATH]
Maintainer tool — re-run after a game update to refresh the names.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MDB = [
    os.path.expandvars(r"%LOCALAPPDATA%Low\Cygames\Umamusume\master\master.mdb"),
    os.path.join(os.path.dirname(REPO), "master_check.mdb"),
    os.path.join(REPO, "master.mdb"),
]
_TITLE = re.compile(r"^\[(.*?)\]\s*(.*)$")


def reformat(text: str) -> str:
    """'[Title] Name' -> 'Name (Title)'. Pass through anything that doesn't match."""
    m = _TITLE.match(str(text or "").strip())
    if not m:
        return str(text or "").strip()
    title, name = m.group(1).strip(), m.group(2).strip()
    return f"{name} ({title})" if title and name else (name or title)


def main():
    ap = argparse.ArgumentParser(description="Build data/card_names_core.json from master.mdb")
    ap.add_argument("--mdb", default=None)
    ap.add_argument("--out", default=os.path.join(REPO, "data", "card_names_core.json"))
    args = ap.parse_args()
    mdb = args.mdb or next((p for p in DEFAULT_MDB if os.path.exists(p)), None)
    if not mdb or not os.path.exists(mdb):
        print("ERROR: master.mdb not found; pass --mdb PATH", file=sys.stderr)
        return 2
    con = sqlite3.connect(mdb)
    out = {}
    for idx, text in con.execute('SELECT "index", text FROM text_data WHERE category=4'):
        try:
            cid = int(idx)
        except (TypeError, ValueError):
            continue
        name = reformat(text)
        if name:
            out[str(cid)] = name
    con.close()
    if len(out) < 10:
        print(f"ERROR: only {len(out)} names — refusing to write.", file=sys.stderr)
        return 3
    tmp = args.out + ".tmp"
    open(tmp, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    os.replace(tmp, args.out)
    print(f"DONE: {len(out)} card names -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
