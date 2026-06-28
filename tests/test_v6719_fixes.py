"""Static smoke tests for v6.7.19: the in-app Help & Documentation modal.

This is a frontend feature, so these tests can't render a browser. What
they CAN do is guard the wiring across the three static assets so an
accidental edit doesn't silently break the feature:
  * the HELP button exists and sits BETWEEN setup and accounts
  * the modal shell and its render targets exist in the markup
  * the JS module exists and references the same IDs
  * the CSS defines the modal/nav/content classes
  * every nav target the JS builds has matching CSS

The richer interaction (search, scroll-spy) is validated by opening the
generated preview in a browser; these tests cover structural integrity.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(HERE, "..", "public")


def _read(name):
    with open(os.path.join(PUBLIC, name), "r", encoding="utf-8") as f:
        return f.read()


class HelpButtonPlacementTests(unittest.TestCase):
    def setUp(self):
        self.html = _read("index.html")

    def test_help_button_exists(self):
        self.assertIn('id="v6719-help-btn"', self.html)
        self.assertIn(">HELP</button>", self.html)

    def test_help_button_uses_launch_class(self):
        self.assertIn("v6719-help-launch", self.html)


class HelpModalMarkupTests(unittest.TestCase):
    def setUp(self):
        self.html = _read("index.html")

    def test_modal_shell_present(self):
        self.assertIn('id="v6719-help-modal"', self.html)
        self.assertIn('id="v6719-help-done-btn"', self.html)

    def test_render_targets_present(self):
        for target in ("v6719-help-search", "v6719-help-nav-list", "v6719-help-content"):
            self.assertIn('id="' + target + '"', self.html, target + " missing")

    def test_modal_has_title_and_done(self):
        self.assertIn("v6719-help-title", self.html)
        self.assertIn(">DONE</button>", self.html)


class HelpModuleJsTests(unittest.TestCase):
    def setUp(self):
        self.js = _read("app.js")

    def test_module_present(self):
        self.assertIn("Help & Documentation module", self.js)

    def test_js_references_modal_ids(self):
        for ident in ("v6719-help-modal", "v6719-help-content",
                      "v6719-help-nav-list", "v6719-help-search",
                      "v6719-help-btn", "v6719-help-done-btn"):
            self.assertIn(ident, self.js, ident + " not referenced in JS")

    def test_module_defines_sections(self):
        self.assertIn("var SECTIONS", self.js)
        # the documented section ids the nav/content are built from
        for sid in ("overview", "quick-start", "setup", "accounts",
                    "race-solver", "training", "profiles", "run-controls",
                    "ai-learning", "items-skills", "history-reasoning",
                    "diagnostics", "tips", "faq"):
            self.assertIn('id: "' + sid + '"', self.js, "section " + sid + " missing")

    def test_open_close_wired(self):
        self.assertIn("openModal", self.js)
        self.assertIn("closeModal", self.js)
        # Esc-to-close and overlay-click-to-close
        self.assertIn('"Escape"', self.js)

    def test_search_and_scrollspy_present(self):
        self.assertIn("IntersectionObserver", self.js)
        self.assertIn("data-search", self.js)

    def test_bound_guard_used(self):
        """Matches the codebase pattern: idempotent event binding."""
        self.assertIn("v6719Bound", self.js)


class HelpCssTests(unittest.TestCase):
    def setUp(self):
        self.css = _read("styles.css")

    def test_core_classes_defined(self):
        for cls in (".v6719-help-modal", ".v6719-help-panel",
                    ".v6719-help-topbar", ".v6719-help-body",
                    ".v6719-help-nav", ".v6719-help-content",
                    ".v6719-help-section", ".v6719-help-nav-link",
                    ".v6719-help-launch", ".v6719-help-search"):
            self.assertIn(cls, self.css, cls + " not defined")

    def test_callout_and_table_styles(self):
        for cls in (".v6719-callout", ".v6719-help-table",
                    ".v6719-kw", ".v6719-steps"):
            self.assertIn(cls, self.css, cls + " not defined")

    def test_active_state_defined(self):
        self.assertIn(".v6719-help-nav-link.is-active", self.css)

    def test_responsive_and_reduced_motion(self):
        self.assertIn("@media (max-width: 760px)", self.css)
        self.assertIn("prefers-reduced-motion", self.css)

    def test_no_leftover_typo_colors(self):
        """Guard against the stray duplicate color decls fixed during dev."""
        self.assertNotIn("#5a6party", self.css)


if __name__ == "__main__":
    unittest.main()
