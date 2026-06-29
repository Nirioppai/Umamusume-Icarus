from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from career_bot.running_style import (
    STYLE_FRONT,
    STYLE_PACE,
    STYLE_LATE,
    STYLE_END,
    normalize_running_style,
    resolve_running_style_for_race,
    resolve_skill_running_style,
    running_style_key,
)
from career_bot.skills import SkillBuyer, SKILL_TAG_PACE, SKILL_TAG_LATE

INDEX = (ROOT / "public" / "index.html").read_text(encoding="utf-8", errors="replace")
APP_JS = (ROOT / "public" / "app.js").read_text(encoding="utf-8", errors="replace")
SHELL = (ROOT / "public" / "css" / "shell.css").read_text(encoding="utf-8", errors="replace")


def test_running_style_game_ids_are_not_zero_based():
    assert normalize_running_style("Front Runner") == STYLE_FRONT
    assert normalize_running_style("Pace Chaser") == STYLE_PACE
    assert normalize_running_style("Late Surger") == STYLE_LATE
    assert normalize_running_style("End Closer") == STYLE_END
    assert normalize_running_style("2") == STYLE_PACE
    assert running_style_key("Pace Chaser") == "pace"


def test_race_style_resolver_prefers_per_distance_then_racing_settings():
    preset = {
        "running_style": 2,
        "mant_config": {
            "enable_per_distance_strategy": True,
            "race_strategy_by_distance": {"mile": "3"},
        },
    }
    assert resolve_running_style_for_race(preset, "mile", 44) == STYLE_LATE
    assert resolve_running_style_for_race(preset, "medium", 44) == STYLE_PACE


def test_skill_style_resolver_uses_racing_settings_when_skill_strategy_is_auto():
    preset = {"running_style": 2, "skill_strategy": {"running_style": "auto"}}
    assert resolve_skill_running_style(preset) == STYLE_PACE


def test_skill_buyer_blocks_style_exclusive_mismatches():
    buyer = SkillBuyer(ROOT)
    buyer.skill_tags = {
        1001: {SKILL_TAG_LATE},
        1002: {SKILL_TAG_PACE},
        1003: set(),
    }
    mismatch, reason = buyer._skill_style_mismatch(1001, "pace")
    assert mismatch
    assert "Pace Chaser" in reason
    assert buyer._skill_style_mismatch(1002, "pace")[0] is False
    assert buyer._skill_style_mismatch(1003, "pace")[0] is False


def test_smart_solver_distance_mode_help_is_present():
    assert "Distance Preference Modes" in APP_JS
    assert "Strict:</b> Only uses preferred distances" in APP_JS
    assert "Balanced:</b> Strongly prefers selected distances" in APP_JS
    assert "Loose:</b> Treats distance preference" in APP_JS
    assert ".solver-mode-help" in SHELL


def test_ai_learning_has_own_button_and_modal_not_diagnostics_card():
    # v2.1 (#15 Diag/AI merge): AI learning no longer has its OWN separate launch
    # button. Diagnostics + AI/Misc are now two tabs of one "DIAG / AI" page,
    # reached via the single diagnostics launch button (v516-diagnostics-btn) and
    # switched with data-diagai-tab. The AI modal still exists as its own modal
    # (it is the "ai" tab) and AI status must still live in that modal, NOT inside
    # the diagnostics card.
    assert 'id="v516-diagnostics-btn"' in INDEX
    assert 'data-diagai-tab="ai"' in INDEX
    assert 'id="v535-ai-learning-modal"' in INDEX
    assert 'id="v535-ai-learning-body"' in INDEX
    diagnostics_card = INDEX.split('id="v516-diagnostics-card"', 1)[1].split('class="v526-discord-setup"', 1)[0]
    assert 'id="v532-ai-status"' not in diagnostics_card


def test_nav_cleanup_css_targets_three_nav_zones():
    assert 'grid-template-areas: "brand main meta"' in SHELL
    assert 'body.dashboard-mode .navbar-main' in SHELL
    assert 'body.dashboard-mode .navbar-meta' in SHELL
