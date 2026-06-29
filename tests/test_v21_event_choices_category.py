"""Support-card events must show under the 'Support Card Events' tab, not be
dumped into Story.

Root cause (orig): every catalog row was tagged support_card_id=0, so the
frontend's `support_card_id <= 0 -> Story` filter put all events under Story and
left the Support tab empty.

Fix: each /api/events row carries a `category` ('story' | 'support_card'); the
frontend splits on category. Catalog rows keep support_card_id 0 (no real card id
in the scraped data) but take category from the scraped row; seen borrowed/rental
events are support_card via their real support_card_id.

Counts are read from the event-effects file's _meta so the test survives a
gametora re-scrape (the corpus grows/shrinks with game updates).
"""
import asyncio
import json
import os
import pathlib
import shutil
import tempfile
import unittest
from collections import Counter


def _expected_counts():
    """Category split from data/event_effects.json _meta.counts (the catalog the
    /api/events backfill lists when no career has run)."""
    base = pathlib.Path(__file__).resolve().parent.parent
    p = base / "data" / "event_effects.json"
    if not p.exists():
        p = base / "data" / "event_effects_game8.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    c = (d.get("_meta") or {}).get("counts") or {}
    return int(c.get("story") or 0), int(c.get("support_card") or 0)


class EventChoicesCategoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.main = main

    def setUp(self):
        # Redirect seen/overrides to an empty temp dir so the merge lists only
        # the game8 catalog (the pre-run state the user was unsure about).
        self._tmp = tempfile.mkdtemp()
        m = self.main
        self._orig_paths = m._event_choice_paths
        m._event_choice_paths = lambda: (
            os.path.join(self._tmp, "events_seen.json"),
            os.path.join(self._tmp, "event_overrides.json"),
        )

    def tearDown(self):
        self.main._event_choice_paths = self._orig_paths
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _events(self, cards=""):
        return asyncio.run(self.main.get_event_choices(cards))["events"]

    def test_catalog_splits_match_meta_counts(self):
        story, support = _expected_counts()
        cats = Counter(e.get("category") for e in self._events())
        self.assertEqual(cats.get("story"), story)
        self.assertEqual(cats.get("support_card"), support)

    def test_support_card_rows_have_no_real_id_but_are_tagged_support(self):
        sup = [e for e in self._events() if e.get("category") == "support_card"]
        self.assertGreater(len(sup), 100)
        # catalog support-card rows carry no card id; category alone routes them.
        self.assertTrue(all(not e.get("support_card_id") for e in sup))

    def test_seen_borrowed_card_event_tagged_support_with_real_id(self):
        seen = os.path.join(self._tmp, "events_seen.json")
        with open(seen, "w", encoding="utf-8") as f:
            json.dump({"seen-sc": {"story_id": "seen-sc", "event_name": "Seen",
                                   "support_card_id": 30164, "num_choices": 2,
                                   "choice_select_indices": [0, 1]}}, f)
        row = next(e for e in self._events() if e["story_id"] == "seen-sc")
        self.assertEqual(row["category"], "support_card")
        self.assertEqual(row["support_card_id"], 30164)

    def test_catalog_pre_populates_even_with_a_deck_filter(self):
        # Regression: a selected deck sends ?cards= which used to gate off the
        # catalog backfill, leaving the panel empty before a career ran. The
        # catalog must now backfill regardless of the cards filter.
        story, support = _expected_counts()
        events = self._events(cards="30164,30099")
        cats = Counter(e.get("category") for e in events)
        self.assertEqual(cats.get("story"), story)
        self.assertEqual(cats.get("support_card"), support)


if __name__ == "__main__":
    unittest.main()
