"""Umamusume `race_scenario` blob parser — full-field race results.

The on-wire `race_scenario` field (base64 of a gzip'd binary blob) encodes the
deterministic race simulation: a header, per-frame positions, and a per-horse
RESULT table (finish order, times, running style). Icarus already decodes only
the *player's* finish_order in runner._parse_race_rank; this module decodes the
WHOLE field so the win-probability model can be calibrated against real,
whole-field ground truth (every horse's strength vs its actual finish), rather
than only the binary did-the-player-win signal.

Struct layout (little-endian) is the documented Umamusume RaceSimulateData
format. It is derived from the MIT-licensed `race_data_parser.py` /
`race_data.proto` by SSHZ.ORG (bundled in UmaLauncher,
github.com/KevinVG207/UmaLauncher, `umalauncher/external/`), reimplemented here
protobuf-free (plain dataclasses, no protobuf dependency). MIT attribution
retained; this is a clean-room port of the binary layout only.

READ-ONLY: nothing here changes how the bot plays.
"""
from __future__ import annotations

import base64
import gzip
import struct
from dataclasses import dataclass


@dataclass
class HorseResult:
    finish_order: int          # 0-based finishing position in the sim
    finish_time: float
    finish_diff_time: float    # gap to the horse ahead
    start_delay_time: float
    guts_order: int
    wiz_order: int
    last_spurt_start_distance: float
    running_style: int         # 1 Nige / 2 Senko / 3 Sashi / 4 Oikomi (0 none)
    defeat: int
    finish_time_raw: float


@dataclass
class RaceScenario:
    version: int
    horse_num: int
    distance_diff_max: float
    horse_results: list        # list[HorseResult]; index i  <->  frame_order i+1


# SSHZ race_data_parser.deserialize_horse_result struct format.
_HORSE_RESULT_FMT = "<ifffBBfBif"
_STAT_KEYS = ("speed", "stamina", "power", "guts", "wiz")


def parse_blob(blob) -> RaceScenario:
    """Decode a *decompressed* race_scenario blob. Raises ValueError if malformed."""
    if not isinstance(blob, (bytes, bytearray)):
        raise ValueError("blob must be bytes")
    n = len(blob)
    off = 0

    def need(size):
        if off + size > n:
            raise ValueError("truncated race_scenario blob")

    need(4)
    max_length = struct.unpack_from("<i", blob, off)[0]      # header content length
    version = struct.unpack_from("<i", blob, off + 4)[0] if off + 8 <= n else 0
    off += 4 + max_length

    need(16)
    distance_diff_max, horse_num, horse_frame_size, horse_result_size = struct.unpack_from("<fiii", blob, off)
    off += 16
    if not (0 < horse_num <= 100) or horse_result_size <= 0:
        raise ValueError("implausible horse_num/result_size")

    need(4)                                                  # padding block 1
    off += 4 + max(0, struct.unpack_from("<i", blob, off)[0])

    need(8)
    frame_count, frame_size = struct.unpack_from("<ii", blob, off)
    off += 8 + max(0, frame_count) * max(0, frame_size)      # skip per-frame data

    need(4)                                                  # padding block 2
    off += 4 + max(0, struct.unpack_from("<i", blob, off)[0])

    results = []
    for _ in range(horse_num):
        if off + horse_result_size > n:
            raise ValueError("truncated horse_result table")
        results.append(HorseResult(*struct.unpack_from(_HORSE_RESULT_FMT, blob, off)))
        off += horse_result_size
    return RaceScenario(version=version, horse_num=horse_num,
                        distance_diff_max=distance_diff_max, horse_results=results)


def parse_b64(scenario_b64) -> RaceScenario:
    """gzip+base64 decode then parse. Raises ValueError on any failure."""
    try:
        blob = gzip.decompress(base64.b64decode(scenario_b64))
    except Exception as exc:                                 # noqa: BLE001 - normalise to ValueError
        raise ValueError("bad race_scenario encoding: %s" % exc)
    return parse_blob(blob)


def _horse_stats(hd):
    """Pull a stat block (if present) out of a race_horse_data entry."""
    out = {}
    for k in _STAT_KEYS:
        v = hd.get(k)
        if v is not None:
            out["wit" if k == "wiz" else k] = v
    return out


def field_results(scenario: RaceScenario, race_horse_data, player_viewer_id=0):
    """Join parsed horse_results with race_horse_data identities (by frame_order).

    Returns a list of per-horse dicts (sorted by finish), each carrying the
    finish info plus identity (viewer_id / chara_id) and any stats the response
    exposed — enough for offline win-prob calibration.
    """
    by_frame = {}
    for hd in race_horse_data or []:
        try:
            fo = int(hd.get("frame_order") or 0)
        except (TypeError, ValueError, AttributeError):
            continue
        if fo:
            by_frame[fo] = hd
    pvid = int(player_viewer_id or 0)
    out = []
    for idx, hr in enumerate(scenario.horse_results):
        frame_order = idx + 1
        hd = by_frame.get(frame_order, {})
        vid = int(hd.get("viewer_id") or 0)
        rec = {
            "frame_order": frame_order,
            "viewer_id": vid,
            "is_player": bool(pvid) and vid == pvid,
            "finish_order": int(hr.finish_order) + 1,           # 1-based for humans
            "finish_time": round(float(hr.finish_time), 4),
            "finish_diff_time": round(float(hr.finish_diff_time), 4),
            "running_style": int(hr.running_style),
            "defeat": int(hr.defeat),
        }
        cid = hd.get("chara_id") if hd.get("chara_id") is not None else hd.get("card_id")
        if cid is not None:
            rec["chara_id"] = cid
        stats = _horse_stats(hd)
        if stats:
            rec["stats"] = stats
        if hd.get("motivation") is not None:
            rec["motivation"] = hd.get("motivation")
        out.append(rec)
    out.sort(key=lambda r: r["finish_order"])
    return out
