# UPDATES.md — Fork Change Log

Living record of what this fork changed, what upstream superseded, and what's
still active. Updated after every version bump.

Referenced by CLAUDE.md (rules) and UPDATING.md (process).

---

## Currently Active Fork Changes

These are the changes that exist in the codebase RIGHT NOW and must be preserved
during upstream updates.

### `career_bot/items.py` — Granular skip reasons

`_skip_buy()` returns string reason codes instead of `True`/`False`.
The caller passes the string through as `skip_reason` (not a generic `"skip_buy"`).

**Reason codes:** `user_excluded`, `skip_wasteful`, `skip_notepad`, `skip_inv_cap`,
`skip_mega_surplus`, `skip_anklet_cap`, `skip_cure_redundant`, `skip_budget`,
`skip_pre_summer`, `skip_low_deck`, `skip_buff_used`

**Depends on:** nothing
**Depended on by:** `log_viewer.html` (`friendlySkipReason()` map, skip reason breakdown)

### `career_bot/items.py` — `_item_cap()` auto_buy priority

`_item_cap()` checks `auto_buy_items` first, then `item_caps`, then `ITEM_INVENTORY_CAPS`.

### `career_bot/items.py` — Threshold tuning

| Constant | Upstream default | Fork value | Why |
|---|---|---|---|
| Ankle weight inventory cap | 3 | 2 | 5 bought / 1 used per run |
| Ankle weight usage threshold | 40 | 18 | Most turns score 20-35 |
| Megaphone small threshold | 11 | 8 | 4-5 unused per run |
| Megaphone medium threshold | 21 | 15 | Same |
| Megaphone large threshold | 35 | 25 | Same |

### `career_bot/items.py` — Pre-climax hammer dump window

Turns 65-73 (configurable via `trackblazer_hammer_dump_start_turn`).
Artisan hammers used on any G1/G2/G3 race. Excess Masters on G1s only.
Invariant: Artisan hammers reach 0 before climax turn 74.

### `career_bot/runner.py` — Pre-race item logging

16-line FORK block after `_reemit_item_use_debug(state)` in `_race()`.
Writes `bot_pre_race_use_selected` and `bot_pre_race_use_result` into the
career report JSON.

**Depends on:** `self.item_manager.last_pre_race_use_selected`
**Depended on by:** `log_viewer.html` (pre-race item display on race turns)

### `log_viewer.html` — Fork-only file

Not shipped by upstream. Contains: AI summary export, clock display, dump window
analytics, cash-out tracking, granular skip reason breakdown, pre-race item timeline.

---

## Superseded Fork Changes (no longer in codebase)

These were our fixes that upstream solved better. Do NOT restore them.

### `main.py` — `manual_aptitude_overrides` (superseded v3.1)

Our fix: added `manual_aptitude_overrides` field to overlay user manual aptitude
picks on top of master-data base.

v3.1 fix: the UI now sends the correct `trainee_name`/`trainee_id` to the solver,
so `_trackblazer_profile_aptitudes()` reads the right trainee's base aptitudes.
Root cause fixed — our overlay is unnecessary.

### `public/app.js` — `solverManualAptitudes` sender (superseded v3.1)

Companion to the above. Also moot because the active UI is now `public-v3/`,
not `public/`.

### `career_bot/runner.py` — `_pace()` pacing system (superseded v3.0)

Removed during v3 merge. v3 has its own delay/jitter system.

---

## Version History

### v3.1 (applied 2026-06-29)

**Upstream additions (kept):**
- Login persistence (trainee/deck/friend survives restarts)
- Per-distance strategy & style overrides save to presets
- Loop run count selector (1/2/3/5/10/infinite)
- Solver follows setup-selected trainee
- 53 shop exclusion items (full list, persisted)
- Event search by character name
- Event forcing targets the running preset
- Glow stick late/finale dump window + correct fan threshold
- Good-Luck Charm fires on high-failure turns
- Per-occurrence race IDs, independent year selection, Apply Manual button
- `DEFAULT_CHARM_FAILURE_RATE_HIGH = 40` in trackblazer_rules.py

**Collisions detected and resolved:**

| Fork change | What v3.1 did | Resolution |
|---|---|---|
| `_skip_buy()` granular reasons | Reverted to `True`/`False` | Restored string reasons |
| `_skip_buy()` caller pass-through | Collapsed to `"skip_buy"` | Restored `or None` pass-through |
| Pre-race item logging (runner.py) | Deleted the 16-line FORK block | Restored the block |
| `manual_aptitude_overrides` (main.py) | Fixed root cause differently | Accepted upstream (superseded) |
| `public/app.js` manual overrides | Legacy UI replaced by v3 UI | Accepted upstream (superseded) |

**No collision:** megaphone/anklet thresholds, hammer dump window, log_viewer.html
