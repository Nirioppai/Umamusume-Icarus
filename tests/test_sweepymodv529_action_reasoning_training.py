from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "public" / "styles.css").read_text(encoding="utf-8")


def test_reasoning_selection_is_locked_across_refreshes():
    assert "selectedReasonKey" in APP
    assert "reasonSelectionLocked" in APP
    assert "function actionReasonKey" in APP
    assert "renderDecisionReasoning(allRows, activeIndex, { scrollActive: false })" in APP
    assert "state.reasonSelectionLocked = true" in APP


def test_live_footer_ticker_is_suppressed_while_running():
    # Footer stays empty while running unless the server is throttling the
    # account (recent rejects/recoveries), in which case it surfaces that.
    assert "Surface server throttling when present" in APP
    assert "setFooterStatus('');" in APP
    assert ".v520-start-status.is-empty" in STYLES
    assert "z-index: 2 !important" in STYLES
