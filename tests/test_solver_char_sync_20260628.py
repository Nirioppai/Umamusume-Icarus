"""Smart Race Solver "Character Preset" must follow the trainee selected in
Setup (issue #1, 2026-06-28).

Root cause: ``/api/character-profile/active`` nests ``card_id`` under
``resolved_from`` (main.py ~4245), but the v3 solver modal read top-level
``a.card_id`` -- so the sync ``cid`` was always 0, the sync never fired, and
``charById(100021)`` fell back to the alphabetically-first roster entry,
"Admire Vega". The earlier in-file "BUG #13 fix" was a false positive for
exactly this reason.

This locks both sides of the contract:
  * backend / data: the roster id-space is ``card_id``; ``100021`` (the stale
    hardcoded default) is NOT a roster id; "Admire Vega" is the trap (first
    alphabetically); ``chara_id == card_id // 100``.
  * frontend: ``public-v3/solver_char_match.js`` resolves an active trainee --
    including owned outfit variants and versioned display names -- to the
    correct roster id, reading ``resolved_from.card_id``.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "trainee_profiles_core.json"
MODULE = ROOT / "public-v3" / "solver_char_match.js"


def _roster():
    """Rebuild the roster exactly as ``/api/character-profile/roster`` does:
    dedup by name, ``id = int(card_id)``, sorted by name."""
    rows = json.loads(DATA.read_text(encoding="utf-8"))
    seen, out = set(), []
    for r in rows:
        name = str(r.get("name") or "").strip()
        cid = r.get("card_id")
        if not name or not cid or name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "id": int(cid)})
    out.sort(key=lambda x: x["name"])
    return out


def test_roster_is_cardid_space_and_admire_vega_is_the_trap():
    roster = _roster()
    ids = {c["id"] for c in roster}
    by_name = {c["name"]: c["id"] for c in roster}

    # The stale hardcoded default is NOT a roster id -> it is the bug trigger.
    assert 100021 not in ids
    # Alphabetically-first == the wrong fallback the bug surfaced.
    assert roster[0]["name"] == "Admire Vega"
    # Air Shakur's real roster id (what the default *should* have been).
    assert by_name.get("Air Shakur") == 103601
    # chara_id invariant the variant-fallback relies on.
    for c in roster:
        assert c["id"] // 100 >= 1000


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node not available")
def test_frontend_resolver_follows_trainee(tmp_path):
    assert MODULE.exists(), "public-v3/solver_char_match.js is missing"
    roster = _roster()
    oguri = next(c["id"] for c in roster if c["name"] == "Oguri Cap")

    harness = tmp_path / "harness.js"
    harness.write_text(
        textwrap.dedent(
            f"""
            const SM = require({json.dumps(str(MODULE))});
            const chars = {json.dumps(roster)};
            const R = (a) => SM.resolveActiveToRoster(a, chars);
            const eq = (got, want, msg) => {{
              if (got !== want) {{ console.error('FAIL', msg, 'got', got, 'want', want); process.exit(1); }}
            }};

            // 1. THE bug: exact card_id from resolved_from -> Air Shakur, not Admire Vega.
            eq(R({{resolved_from:{{card_id:103601,selected_name:'Air Shakur'}}}}), 103601, 'exact-card_id');
            // 2. Owned outfit variant (different card_id, same chara_id) -> base roster id.
            eq(R({{resolved_from:{{card_id:103699,selected_name:'Air Shakur (Alt)'}}}}), 103601, 'outfit-variant');
            // 3. No card_id, versioned display name -> name match (suffix stripped).
            eq(R({{resolved_from:{{card_id:0,selected_name:'Oguri Cap (Christmas)'}}}}), {oguri}, 'versioned-name');
            // 4. chara_id only (card_id missing) -> resolves via chara_id.
            eq(R({{resolved_from:{{card_id:0,chara_id:1036}}}}), 103601, 'chara_id-only');
            // 5. Legacy top-level shape is still tolerated.
            eq(R({{card_id:103601}}), 103601, 'legacy-top-level');
            // 6. Nothing resolvable -> null (caller keeps its own roster fallback).
            eq(R({{resolved_from:{{}}}}), null, 'empty');
            eq(R(null), null, 'null');
            eq(R({{resolved_from:{{card_id:0,selected_name:'No Such Trainee'}}}}), null, 'unknown-name');

            console.log('OK');
            """
        ),
        encoding="utf-8",
    )
    res = subprocess.run([NODE, str(harness)], capture_output=True, text=True)
    assert res.returncode == 0, f"node resolver test failed:\n{res.stdout}\n{res.stderr}"


@pytest.mark.skipif(NODE is None, reason="node not available")
def test_modal_reads_resolved_from_and_uses_module():
    """Guard the wiring: the modal must consume the shared resolver and the
    resolver must read the nested ``resolved_from`` field (the exact thing that
    was broken). Cheap source-contract check so a regression is loud."""
    modals = (ROOT / "public-v3" / "modals.js").read_text(encoding="utf-8")
    assert "IcarusSolverMatch" in modals, "modals.js no longer uses the shared resolver"
    module_src = MODULE.read_text(encoding="utf-8")
    assert "resolved_from" in module_src, "resolver no longer reads resolved_from"
