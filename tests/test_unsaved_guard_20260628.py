"""Unsaved-changes guard for settings modals (#4, 2026-06-28).

The interaction is DOM-heavy and the repo has no jsdom harness, so these are
source-contract guards: they lock the wiring that the live behavior depends on,
so a regression (someone dropping the guard from a close path or a modal) fails
loudly. The behavior itself is manually live-verified (see the design doc).

Contract:
  * core.js close paths (DONE/X, backdrop, Esc) route through a per-overlay
    _guardClose hook (attemptClose), and escClose honors the topmost guard.
  * modals.js wireSave installs _guardClose using the modal's own SAVE_COLLECTOR
    snapshot (_cleanSnap), armUnsavedGuard is defined, and the confirm popup
    offers SAVE + DISCARD.
  * every one of the 8 settings modals arms the guard after init.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "public-v3" / "core.js"
MODALS = ROOT / "public-v3" / "modals.js"


def test_core_routes_closes_through_guard():
    src = CORE.read_text(encoding="utf-8")
    assert "_guardClose" in src, "core.js does not consult a guard hook"
    assert "attemptClose" in src, "core.js close paths not funnelled through attemptClose"
    # escClose must defer to the topmost overlay's guard, not unconditionally close.
    m = re.search(r"function escClose\b.*?\n  \}", src, re.S)
    assert m, "escClose not found"
    assert "_guardClose" in m.group(0), "escClose ignores the guard"


def test_modals_install_guard_with_collector_snapshot():
    src = MODALS.read_text(encoding="utf-8")
    assert "_guardClose" in src, "wireSave does not install a guard"
    assert "_cleanSnap" in src, "no clean-state baseline (_cleanSnap)"
    assert "armUnsavedGuard" in src, "no armUnsavedGuard helper"
    assert "showUnsavedConfirm" in src, "no confirm popup"
    # snapshot must be driven by the save collector (precise dirty = saveable change).
    assert "SAVE_COLLECTORS[" in src


def test_confirm_popup_has_save_and_discard():
    src = MODALS.read_text(encoding="utf-8")
    assert "data-uc-save" in src, "confirm popup missing SAVE action"
    assert "data-uc-discard" in src, "confirm popup missing DISCARD action"


def test_all_eight_settings_modals_arm_the_guard():
    src = MODALS.read_text(encoding="utf-8")
    # 1 definition + 8 modal arm calls (training, racing, scenario, solver,
    # skills, customDeck, userdata, discord).
    n = src.count("armUnsavedGuard(")
    assert n >= 9, f"expected >=9 armUnsavedGuard occurrences (def + 8 modals), got {n}"


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node not available")
def test_js_syntax_ok():
    for f in (CORE, MODALS):
        r = subprocess.run([NODE, "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{f.name} syntax error:\n{r.stderr}"
