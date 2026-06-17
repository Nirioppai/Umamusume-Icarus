from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nav_uses_carrots_label_not_jewels():
    app = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
    assert "JEWELS" not in app
    assert "Jewels" not in app
    assert "CARROTS" in app
    assert "Carrots Only" in app


def test_theme_logout_nav_cleanup_css_present():
    shell = (ROOT / "public" / "css" / "shell.css").read_text(encoding="utf-8")
    assert "v5.30: top-right nav cleanup" in shell
    assert "body.dashboard-mode .navbar-meta" in shell
    assert "body.dashboard-mode .run-count-control" in shell


def test_skill_list_scroll_preservation_present():
    app = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
    assert "weightedSkillListScrollTop" in app
    assert "skillListScrollTop" in app
