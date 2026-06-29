#!/usr/bin/env python3
"""
extract_game_icons.py  —  Pull HIGH-RES character + support-card icons straight
from the locally-installed Umamusume (Steam/Global) game assets and use them to
replace the bot's low-res 128x128 palette PNGs in data/images/.

How it works (all reverse-engineered from katboi01/UmaViewer):
  1. The asset manifest (`<game>/meta`) is an SQLite3MC database (ChaCha20 cipher,
     index 3). The raw key = GenFinalKey(GlobalDBKey) = GlobalDBKey[i] ^ DBBaseKey[i%13].
     We read it with apsw-sqlite3mc.  Table `a`: m,n,h,c,d,e =
     type, name, hash(url), checksum, prerequisites, Key(Int64).
  2. Each asset bundle lives at `<game>/dat/<h[:2]>/<h>` and is a standard UnityFS
     bundle XOR-masked from byte offset 256 with a per-file key (FKey):
         FKey = 88 bytes;  FKey[i*8 + j] = ABKey[i] ^ keyBytes[j]
         where ABKey = 53 2B 46 31 E4 A7 B9 47 3E 7C FB (11 bytes) and
         keyBytes = struct.pack('<q', Key)  (the Int64 from column e).
         un-mask:  data[i] ^= FKey[i % 88]   for i >= 256
  3. The un-masked bytes are a normal UnityFS bundle -> UnityPy -> Texture2D -> PNG.

Mapping bot id -> game asset name:
  * 5-digit id (support card)  -> supportcard/support{id}/support_card_s_{id}
  * 6-digit id (character card)-> chara/chr{id//100}/chr_icon_{id//100}_{id}_01
                                   (falls back to _02, then the round chr_icon_{id//100})

Requires (one-time):  pip install apsw-sqlite3mc UnityPy pillow
Re-run after a game update to refresh the icons. Dev-only tool; do NOT ship the
extracted-from-game pipeline in beta/public builds (this script can stay; it just
won't run without the game install).
"""
from __future__ import annotations
import argparse
import os
import shutil
import struct
import sys
import tempfile
import zipfile

# ---- constants reverse-engineered from UmaViewer Config.json + source ----
GLOBAL_DB_KEY = bytes.fromhex("56636B634272377665704162")          # b"VckcBr7vepAb"
DB_BASE_KEY   = bytes.fromhex("F170CEA4DFCEA3E1A5D8C70BD1000000")  # 16 bytes
AB_KEY        = bytes.fromhex("532B4631E4A7B9473E7CFB")            # 11 bytes
XOR_HEADER    = 256                                                 # first 256 bytes unmasked

DEFAULT_GAME = os.path.expandvars(r"%LOCALAPPDATA%Low\Cygames\Umamusume")


def gen_final_key(key: bytes) -> bytes:
    """UmaViewer GenFinalKey: key[i] ^= DBBaseKey[i % 13]."""
    if len(DB_BASE_KEY) < 13:
        raise ValueError("DB base key too short")
    return bytes(key[i] ^ DB_BASE_KEY[i % 13] for i in range(len(key)))


def open_meta(game_dir: str):
    """Copy the (locked/encrypted) meta to a temp file and open it via apsw-sqlite3mc."""
    import apsw
    src = os.path.join(game_dir, "meta")
    if not os.path.exists(src):
        raise FileNotFoundError(f"meta manifest not found at {src}")
    tmp = os.path.join(tempfile.gettempdir(), "uma_meta_extract.db")
    shutil.copyfile(src, tmp)
    final = gen_final_key(GLOBAL_DB_KEY)
    con = apsw.Connection(tmp)
    con.execute("PRAGMA cipher='chacha20'")
    con.execute("PRAGMA hexkey='%s'" % final.hex())
    # sanity check
    con.execute("SELECT count(*) FROM a").fetchone()
    return con


def fkey_for(key_val: int) -> bytes:
    kb = struct.pack("<q", key_val)            # Int64 little-endian -> 8 bytes
    out = bytearray(len(AB_KEY) * 8)           # 88 bytes
    for i in range(len(AB_KEY)):
        for j in range(8):
            out[i * 8 + j] = AB_KEY[i] ^ kb[j]
    return bytes(out)


def unmask(data: bytearray, key_val: int) -> bytearray:
    if not key_val:
        return data                            # unencrypted entry -> no XOR
    fk = fkey_for(key_val)
    L = len(fk)
    for i in range(XOR_HEADER, len(data)):
        data[i] ^= fk[i % L]
    return data


def extract_texture(game_dir: str, h: str, key_val: int):
    """Return a PIL image for the first Texture2D in the bundle, or None."""
    import UnityPy
    path = os.path.join(game_dir, "dat", h[:2], h)
    if not os.path.exists(path):
        return None
    data = unmask(bytearray(open(path, "rb").read()), key_val)
    tmp = tempfile.mktemp(suffix=".unity3d")
    try:
        open(tmp, "wb").write(data)
        env = UnityPy.load(tmp)
        best = None
        for o in env.objects:
            if o.type.name == "Texture2D":
                img = o.read().image
                if best is None or (img.size[0] * img.size[1]) > (best.size[0] * best.size[1]):
                    best = img
        return best
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def asset_candidates(bot_id: str):
    """Yield candidate game asset names for a bot image id (most-preferred first)."""
    if len(bot_id) == 5:                       # support card
        yield f"supportcard/support{bot_id}/support_card_s_{bot_id}"
        yield f"supportcard/support{bot_id}/support_thumb_{bot_id}"
    elif len(bot_id) == 6:                      # character card
        chara = bot_id[:4]
        yield f"chara/chr{chara}/chr_icon_{chara}_{bot_id}_01"
        yield f"chara/chr{chara}/chr_icon_{chara}_{bot_id}_02"
        yield f"chara/chr{chara}/chr_icon_{chara}"   # round per-character fallback


def main():
    ap = argparse.ArgumentParser(description="Extract high-res Umamusume icons into data/images")
    ap.add_argument("--game", default=DEFAULT_GAME, help="game install dir (contains meta + dat/)")
    ap.add_argument("--images", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "images"),
                    help="bot icon dir to refresh (default: <repo>/data/images)")
    ap.add_argument("--backup", default=None, help="zip path for the originals (default: alongside repo)")
    ap.add_argument("--only", default=None, help="comma-separated ids to do (debug)")
    ap.add_argument("--dry-run", action="store_true", help="report mapping only; write nothing")
    args = ap.parse_args()

    if not os.path.isdir(args.images):
        print(f"ERROR: images dir not found: {args.images}", file=sys.stderr)
        return 2

    ids = ([s.strip() for s in args.only.split(",")] if args.only
           else sorted(os.path.splitext(f)[0] for f in os.listdir(args.images) if f.lower().endswith(".png")))
    print(f"{len(ids)} bot icons to refresh from {args.game}")

    # back up originals first (outside the served dir)
    if not args.dry_run and not args.only:
        backup = args.backup or os.path.join(os.path.dirname(os.path.dirname(args.images)),
                                             "icons_lowres_backup.zip")
        with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as z:
            for f in os.listdir(args.images):
                if f.lower().endswith(".png"):
                    z.write(os.path.join(args.images, f), f)
        print(f"backed up originals -> {backup}")

    con = open_meta(args.game)
    rows = con.execute("SELECT n,h,e FROM a").fetchall()
    by_name = {n: (h, e) for (n, h, e) in rows}
    print(f"meta loaded: {len(by_name)} assets")

    ok = miss = fail = 0
    misses = []
    for bot_id in ids:
        chosen = next((c for c in asset_candidates(bot_id) if c in by_name), None)
        if not chosen:
            miss += 1
            misses.append(bot_id)
            continue
        if args.dry_run:
            ok += 1
            continue
        h, e = by_name[chosen]
        try:
            img = extract_texture(args.game, h, e)
            if img is None:
                fail += 1
                continue
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            img.save(os.path.join(args.images, f"{bot_id}.png"))
            ok += 1
        except Exception as ex:  # noqa: BLE001
            fail += 1
            print(f"  FAIL {bot_id} ({chosen}): {ex}")
        if ok and ok % 100 == 0:
            print(f"  ...{ok} done")

    print(f"\nDONE: {ok} extracted, {miss} unmapped, {fail} failed (of {len(ids)})")
    if misses:
        print("unmapped ids (kept original):", ", ".join(misses[:40]) + (" ..." if len(misses) > 40 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
