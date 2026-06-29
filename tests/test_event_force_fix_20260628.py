"""Forced event choices must actually apply (2026-06-28).

Two confirmed root causes in career_bot/events.py:
  * Bug A (key mismatch): the Event Choices panel saves overrides keyed by the
    gametora catalog key (a slug for not-yet-seen events), but the runner's
    _override_choice only matched the live numeric story_id/event_id/chara:title
    -> catalog-keyed overrides never resolved -> choice not forced at all.
  * Bug B (value semantics): the override value is a 0-based choice POSITION, but
    _choice_index_from_select matched it as a game select_index first (1-based),
    so forcing the 2nd+ choice selected the one before it.
"""

import tempfile
import unittest
from pathlib import Path

from career_bot.events import EventManager


def live_event(name, story_id="400099001", n=2):
    """A live event payload as the game sends it: numeric story_id + a title,
    n choices with 1-based select_index in array order."""
    return {
        "story_id": story_id,
        "event_id": int(story_id),
        "title": name,
        "event_contents_info": {
            "choice_array": [
                {"select_index": i + 1, "params_inc_dec_info_array": [{"target_type": 1, "value": 10}]}
                for i in range(n)
            ]
        },
    }


class EventForceFixTests(unittest.TestCase):
    def _mgr(self, catalog=None):
        m = EventManager(Path(tempfile.mkdtemp()))
        m.scraped_effects = catalog or {}
        m._scraped_name_index = None
        m._override_key_index = None
        return m

    # ---- Bug A: catalog-slug override resolves to the live event by name ----
    def test_catalog_slug_override_applies_via_name(self):
        catalog = {
            "some-slug": {
                "event_name": "My Event",
                "choices": {"1": {"effect": "Speed +10"}, "2": {"effect": "Stamina +10"}},
            }
        }
        m = self._mgr(catalog)
        preset = {"event_overrides": {"some-slug": 1}}  # force the 2nd choice (position 1)
        idx = m.choose(live_event("My Event"), preset, 25, {"vital": 80, "motivation": 5})
        self.assertEqual(m.last_choice_trace.get("reason"), "preset_override")
        self.assertEqual(idx, 1)

    def test_catalog_slug_override_name_normalized(self):
        # whitespace/case differences between live title and catalog name still match
        catalog = {"slug2": {"event_name": "Extra   Training",
                             "choices": {"1": {"effect": "a"}, "2": {"effect": "b"}}}}
        m = self._mgr(catalog)
        preset = {"event_overrides": {"slug2": 0}}
        ev = live_event("extra training", story_id="400099009")
        idx = m.choose(ev, preset, 25, {"vital": 80, "motivation": 5})
        self.assertEqual(m.last_choice_trace.get("reason"), "preset_override")
        self.assertEqual(idx, 0)

    # ---- Bug B: a 0-based position override selects exactly that position ----
    def test_position_override_selects_that_position(self):
        m = self._mgr()
        ev = live_event("Whatever", story_id="400099002", n=3)
        preset = {"event_overrides": {"400099002": 2}}  # force the 3rd choice (position 2)
        idx = m.choose(ev, preset, 25, {"vital": 80, "motivation": 5})
        self.assertEqual(m.last_choice_trace.get("reason"), "preset_override")
        self.assertEqual(idx, 2)

    def test_position_zero_selects_first(self):
        m = self._mgr()
        ev = live_event("Whatever", story_id="400099003", n=2)
        idx = m.choose(ev, {"event_overrides": {"400099003": 0}}, 25, {"vital": 80, "motivation": 5})
        self.assertEqual(idx, 0)

    # ---- regression: a seen-event override keyed by the live numeric id still works ----
    def test_direct_numeric_key_still_matches(self):
        m = self._mgr()
        ev = live_event("Whatever", story_id="400099004", n=2)
        idx = m.choose(ev, {"event_overrides": {"400099004": 1}}, 25, {"vital": 80, "motivation": 5})
        self.assertEqual(m.last_choice_trace.get("reason"), "preset_override")
        self.assertEqual(idx, 1)

    def test_choice_index_from_select_unit(self):
        m = self._mgr()
        choices = [{"select_index": 1}, {"select_index": 2}, {"select_index": 3}]
        self.assertEqual(m._choice_index_from_select(choices, 0), 0)
        self.assertEqual(m._choice_index_from_select(choices, 1), 1)
        self.assertEqual(m._choice_index_from_select(choices, 2), 2)


if __name__ == "__main__":
    unittest.main()
