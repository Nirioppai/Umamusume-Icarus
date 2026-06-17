"""Umabot TP recovery payload and ordering tests adapted for SweepyMod."""
import sys
import types

if "curl_cffi" not in sys.modules:
    module = types.ModuleType("curl_cffi")
    module.requests = types.SimpleNamespace(
        Session=lambda: types.SimpleNamespace(headers={}, post=None, close=lambda: None)
    )
    sys.modules["curl_cffi"] = module

if "Crypto" not in sys.modules:
    crypto = types.ModuleType("Crypto")
    cipher_pkg = types.ModuleType("Crypto.Cipher")
    aes_mod = types.ModuleType("Crypto.Cipher.AES")
    aes_mod.MODE_CBC = 1
    aes_mod.new = lambda *a, **k: types.SimpleNamespace(encrypt=lambda b: b, decrypt=lambda b: b)
    util_pkg = types.ModuleType("Crypto.Util")
    padding_mod = types.ModuleType("Crypto.Util.Padding")
    padding_mod.pad = lambda b, n: b
    padding_mod.unpad = lambda b, n: b
    sys.modules.update({
        "Crypto": crypto,
        "Crypto.Cipher": cipher_pkg,
        "Crypto.Cipher.AES": aes_mod,
        "Crypto.Util": util_pkg,
        "Crypto.Util.Padding": padding_mod,
    })

import uma_api.client as client_mod
from uma_api.client import UmaClient

client_mod.get_hwid = lambda seed="default": {
    "udid": "00000000-0000-0000-0000-000000000000",
    "device_id": "x",
    "device_name": "x",
    "graphics_device_name": "x",
    "ip_address": "127.0.0.1",
    "platform_os_version": "Windows 10",
}


def make_client():
    c = UmaClient({"viewer_id": 327875345340, "steam_password_seed": "test"}, trace_enabled=False)
    c.calls = []
    def fake_call(ep, args=None, **kwargs):
        c.calls.append((ep, dict(args or {})))
        return c.next_response.pop(0) if getattr(c, "next_response", None) else {"data": {}}
    c.call = fake_call
    return c


def test_use_recovery_item_payload_matches_umabot_capture():
    c = make_client()
    c.item_map[32] = 82
    c.next_response = [{"data": {"tp_info": {"current_tp": 130, "max_tp": 100}}}]
    c.use_recovery_item(item_num=1)
    ep, payload = c.calls[0]
    assert ep == "item/use_recovery_item"
    assert payload == {"item_id": 32, "client_own_num": 82, "item_num": 1}
    assert c.tp_info["current_tp"] == 130


def test_use_recovery_item_decrements_local_count_without_server_list():
    c = make_client()
    c.item_map[32] = 5
    c.next_response = [{"data": {"tp_info": {"current_tp": 60}}}]
    c.use_recovery_item(item_num=1)
    assert c.tp_potion_count() == 4


def test_use_recovery_item_prefers_server_item_count():
    c = make_client()
    c.item_map[32] = 5
    c.next_response = [{"data": {"tp_info": {"current_tp": 60}, "user_item": [{"item_id": 32, "number": 81}]}}]
    c.use_recovery_item(item_num=1)
    assert c.tp_potion_count() == 81


def test_recovery_tp_sends_total_jewels():
    c = make_client()
    c.coin_info = {"fcoin": 1200, "coin": 300}
    c.next_response = [{"data": {"tp_info": {"current_tp": 100}}}]
    c.recovery_tp(2)
    ep, payload = c.calls[0]
    assert ep == "user/recovery_trainer_point"
    assert payload == {"count": 2, "client_own_num": 1500}


def simulate_recovery(client, use_tp, mode="potion_first", tp_per_potion=30):
    current_tp = int(client.tp_info.get("current_tp") or 0)
    if use_tp and current_tp < use_tp and mode in ("potion_first", "potion_only"):
        for _ in range(20):
            if current_tp >= use_tp or client.tp_potion_count() <= 0:
                break
            client.next_response = [{"data": {"tp_info": {"current_tp": current_tp + tp_per_potion}}}]
            client.use_recovery_item(item_num=1)
            new_tp = int(client.tp_info.get("current_tp") or 0)
            if new_tp <= current_tp:
                break
            current_tp = new_tp
    if use_tp and current_tp < use_tp and mode in ("potion_first", "jewels_only"):
        needed = ((use_tp - current_tp) + 29) // 30
        client.next_response = [{"data": {"tp_info": {"current_tp": current_tp + needed * 30}}}]
        client.recovery_tp(needed)
        current_tp = int(client.tp_info.get("current_tp") or 0)
    return current_tp


def test_potions_used_before_jewels():
    c = make_client()
    c.tp_info = {"current_tp": 0}
    c.item_map[32] = 82
    c.coin_info = {"fcoin": 99999, "coin": 0}
    assert simulate_recovery(c, 30) >= 30
    assert [ep for ep, _ in c.calls] == ["item/use_recovery_item"]
    assert c.tp_potion_count() == 81


def test_potion_first_falls_back_to_jewels_when_items_run_out():
    c = make_client()
    c.tp_info = {"current_tp": 0}
    c.item_map[32] = 1
    c.coin_info = {"fcoin": 99999, "coin": 0}
    assert simulate_recovery(c, 60) >= 60
    assert [ep for ep, _ in c.calls] == ["item/use_recovery_item", "user/recovery_trainer_point"]
