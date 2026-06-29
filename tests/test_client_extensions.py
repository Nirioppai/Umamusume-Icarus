"""Tests for the UmaClient additions that back the API capability batch:
  * response caching (_cache_response) so /api/latent reads last load/index +
    single_mode_free/load + data_headers with NO new API call;
  * thin wrapper methods for endpoints the bot didn't wrap (home_index, item_use,
    support_card_enhance, chara_talent, chara_nickname) — payloads are INFERRED
    (documented as such); these just shape the dict and delegate to call().

A bare instance (__new__, no network __init__) with call() stubbed is used so the
tests don't touch the registry/network.
"""
import unittest

from uma_api.client import UmaClient


def _bare_client():
    c = UmaClient.__new__(UmaClient)
    c.last_account_data = {}
    c.last_career_data = {}
    c.last_data_headers = {}
    c.item_map = {}
    c._calls = []

    def fake_call(ep, args=None, **kw):
        c._calls.append((ep, args or {}, kw))
        return {"data_headers": {"result_code": 1}, "data": {}}

    c.call = fake_call
    return c


class TestCacheResponse(unittest.TestCase):
    def test_caches_load_index_and_headers(self):
        c = _bare_client()
        UmaClient._cache_response(c, "load/index",
                                  {"data_headers": {"server_time": 9, "result_code": 1},
                                   "data": {"tp_info": {"current_tp": 5}}})
        self.assertEqual(c.last_account_data["tp_info"]["current_tp"], 5)
        self.assertEqual(c.last_data_headers["server_time"], 9)
        self.assertEqual(c.last_career_data, {})

    def test_caches_career_load(self):
        c = _bare_client()
        UmaClient._cache_response(c, "single_mode_free/load",
                                  {"data": {"chara_info": {"turn": 7}}})
        self.assertEqual(c.last_career_data["chara_info"]["turn"], 7)

    def test_caches_career_start(self):
        c = _bare_client()
        UmaClient._cache_response(c, "single_mode_free/start", {"data": {"chara_info": {"turn": 1}}})
        self.assertEqual(c.last_career_data["chara_info"]["turn"], 1)

    def test_ignores_unrelated_endpoint_for_data_but_keeps_headers(self):
        c = _bare_client()
        UmaClient._cache_response(c, "home/index", {"data_headers": {"server_time": 3}, "data": {"x": 1}})
        self.assertEqual(c.last_account_data, {})
        self.assertEqual(c.last_career_data, {})
        self.assertEqual(c.last_data_headers["server_time"], 3)

    def test_non_dict_response_safe(self):
        c = _bare_client()
        UmaClient._cache_response(c, "load/index", "not-a-dict")  # must not raise
        self.assertEqual(c.last_account_data, {})


class TestWrapperMethods(unittest.TestCase):
    def test_home_index(self):
        c = _bare_client()
        UmaClient.home_index(c)
        self.assertEqual(c._calls[-1][0], "home/index")

    def test_item_use_uses_owned_count(self):
        c = _bare_client()
        c.item_map = {50: 4}
        UmaClient.item_use(c, item_id=50, item_num=2)
        ep, args, _ = c._calls[-1]
        self.assertEqual(ep, "item/use")
        self.assertEqual(args["item_id"], 50)
        self.assertEqual(args["item_num"], 2)
        self.assertEqual(args["client_own_num"], 4)

    def test_support_card_enhance(self):
        c = _bare_client()
        UmaClient.support_card_enhance(c, support_card_id=30001,
                                       use_item_info_array=[{"item_id": 1, "item_num": 3}])
        ep, args, _ = c._calls[-1]
        self.assertEqual(ep, "support_card/enhance")
        self.assertEqual(args["support_card_id"], 30001)
        self.assertEqual(args["use_item_info_array"], [{"item_id": 1, "item_num": 3}])

    def test_chara_talent(self):
        c = _bare_client()
        UmaClient.chara_talent(c, trained_chara_id=7, rank_up_target_rank=2)
        ep, args, _ = c._calls[-1]
        self.assertEqual(ep, "chara/talent")
        self.assertEqual(args["trained_chara_id"], 7)
        self.assertEqual(args["rank_up_target_rank"], 2)

    def test_chara_nickname(self):
        c = _bare_client()
        UmaClient.chara_nickname(c, trained_chara_id=7, nickname_id=101)
        ep, args, _ = c._calls[-1]
        self.assertEqual(ep, "chara/nickname")
        self.assertEqual(args["nickname_id"], 101)


if __name__ == "__main__":
    unittest.main()
