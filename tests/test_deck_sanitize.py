"""Tests for the support-deck sanitizer that prevents result_code 2511.

The game rejects single_mode_free/start when the deck is illegal: more than 6
cards total, the borrowed friend duplicated among the owned cards, or duplicate
owned cards. The sanitizer makes the owned support list legal before start.
"""
from uma_api.deck_sanitize import sanitize_support_deck


def test_removes_friend_from_owned_deck():
    # The borrowed friend (30) must not ALSO be an owned support card.
    assert sanitize_support_deck([10, 20, 30, 40, 50], 30) == [10, 20, 40, 50]


def test_friend_in_deck_with_oversize_stays_legal():
    # friend=3 is in the deck AND the deck is 6 long -> drop the friend, cap 5.
    out = sanitize_support_deck([1, 2, 3, 4, 5, 6], 3)
    assert 3 not in out
    assert len(out) <= 5
    assert out == [1, 2, 4, 5, 6]


def test_caps_to_five_when_friend_present():
    # 6 owned + a borrowed friend = 7 total -> trim owned to 5 (5 + friend = 6).
    assert sanitize_support_deck([1, 2, 3, 4, 5, 6], 99) == [1, 2, 3, 4, 5]


def test_caps_to_six_when_no_friend():
    # No borrowed friend -> a full 6 owned cards is legal; 7 trims to 6.
    assert sanitize_support_deck([1, 2, 3, 4, 5, 6, 7], 0) == [1, 2, 3, 4, 5, 6]


def test_removes_duplicate_owned_cards():
    assert sanitize_support_deck([10, 10, 20, 20, 30], 0) == [10, 20, 30]


def test_drops_blank_and_invalid_ids():
    assert sanitize_support_deck([1, 0, 2, None, 3, ""], 0) == [1, 2, 3]


def test_preserves_original_element_types():
    # Caller may pass strings; preserve the original elements (compare by int).
    assert sanitize_support_deck(["1", "2", "2"], "0") == ["1", "2"]


def test_handles_empty_and_none():
    assert sanitize_support_deck([], 0) == []
    assert sanitize_support_deck(None, 0) == []


def test_legal_deck_unchanged():
    # 5 owned + a distinct borrowed friend is already legal -> returned as-is.
    assert sanitize_support_deck([1, 2, 3, 4, 5], 6) == [1, 2, 3, 4, 5]
