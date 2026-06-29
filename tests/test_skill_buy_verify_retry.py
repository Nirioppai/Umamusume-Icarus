"""Regression for the web-intercept skill-buy failure (career_log_20260626_220720).

When the web skill-intercept blocks the runner for minutes while the user decides,
the game refuses the late gain_skills with result_code 205, and a following 208
'busy' envelope (client.py returns it without raising for gain_skills) made
_buy_batch record the buy as "ok" with 0 skills actually granted — a silent
failure. The fix: verify the grant against a reloaded state, retry on a genuine
non-grant, and only mark skills acquired / record "ok" once a grant is confirmed.
"""
import unittest
from pathlib import Path

from career_bot.skills import SkillBuyer

BASE = Path(__file__).resolve().parents[1]


class FakeClient:
    """gain_skills returns successive canned responses (the last repeats);
    load_career returns successive canned states (the last repeats)."""
    def __init__(self, gain_results, load_states):
        self.gain_results = list(gain_results)
        self.load_states = list(load_states)
        self.gain_calls = 0
        self.load_calls = 0

    def gain_skills(self, payload, turn):
        self.gain_calls += 1
        r = self.gain_results[min(self.gain_calls - 1, len(self.gain_results) - 1)]
        if isinstance(r, Exception):
            raise r
        return r

    def load_career(self):
        self.load_calls += 1
        return self.load_states[min(self.load_calls - 1, len(self.load_states) - 1)]


def _gain_res(rc, owned=None, sp=None):
    data = {}
    ci = {}
    if owned is not None:
        ci["skill_array"] = [{"skill_id": s} for s in owned]
    if sp is not None:
        ci["skill_point"] = sp
    if ci:
        data["chara_info"] = ci
    return {"data_headers": {"result_code": rc}, "data": data}


def _load_state(owned, sp=450):
    return {"data": {"chara_info": {"skill_point": sp, "skill_array": [{"skill_id": s} for s in owned]}}}


def _setup(buyer, skill_point=500):
    # Use a real (group_id, skill_id) from the buyer's own data so preflight passes.
    gid, sids = next(iter(buyer.group_to_skill_ids.items()))
    sid = int(sids[0])
    chara = {
        "turn": 30, "skill_point": skill_point,
        "skill_array": [],
        "skill_tips_array": [{"group_id": gid}],
    }
    state = {"data": {"chara_info": chara}}
    cands = [{"skill_id": sid, "cost": 50, "bundled_skill_ids": []}]
    return state, cands, sid


class VerifyRetryTests(unittest.TestCase):
    def test_208_envelope_but_grant_confirmed_via_reload(self):
        b = SkillBuyer(BASE)
        state, cands, sid = _setup(b)
        # gain_skills reports 208 (busy, no grant visible); a reload shows it WAS granted.
        client = FakeClient(gain_results=[_gain_res(208)], load_states=[_load_state([sid])])
        merged, count = b._buy_batch(client, state, cands, 30)
        self.assertEqual(count, 1)
        self.assertEqual(b.last_result.get("result"), "ok")
        self.assertIn(sid, b._acquired_skill_ids)

    def test_persistent_non_grant_fails_and_is_not_marked(self):
        b = SkillBuyer(BASE)
        state, cands, sid = _setup(b)
        # gain_skills never grants (busy), reload never shows it owned.
        client = FakeClient(gain_results=[_gain_res(208)], load_states=[_load_state([], sp=500)])
        merged, count = b._buy_batch(client, state, cands, 30)
        self.assertEqual(count, 0)
        self.assertEqual(b.last_result.get("result"), "failed")
        self.assertNotIn(sid, b._acquired_skill_ids,
                         "a failed buy must NOT be marked acquired, so it can retry on a later turn")
        self.assertGreaterEqual(client.gain_calls, 2, "should have retried the buy")

    def test_clean_success_first_attempt_no_retry(self):
        b = SkillBuyer(BASE)
        state, cands, sid = _setup(b)
        client = FakeClient(gain_results=[_gain_res(1, owned=[sid], sp=450)], load_states=[_load_state([sid])])
        merged, count = b._buy_batch(client, state, cands, 30)
        self.assertEqual(count, 1)
        self.assertEqual(b.last_result.get("result"), "ok")
        self.assertEqual(client.gain_calls, 1, "a clean success must not trigger extra retries")
        self.assertIn(sid, b._acquired_skill_ids)


if __name__ == "__main__":
    unittest.main()
