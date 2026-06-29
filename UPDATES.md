# UPDATES.md — Fork Change Log

Living record of every fork modification with date and context.
Updated after every fork change AND every upstream version bump.

Referenced by [CLAUDE.md](CLAUDE.md) (rules) and [UPDATING.md](UPDATING.md) (process).

---

## Entry Format

Every entry follows this exact format. No exceptions.

```
### YYYY-MM-DD — <short title>
**Commit:** `<hash>` **File(s):** `<path>` [, `<path>`]
**Context:** <why this change was made — the problem it solves, not what it does>
**Status:** ACTIVE | SUPERSEDED (by <what>) | RESTORED (after <version>)
```

---

## Change Log

### 2026-06-25 — Pacing system
**Commit:** `3b8e236` **File(s):** `career_bot/runner.py`, `career_bot/delay.py`
**Context:** Bot actions were instant, making the request pattern machine-like. Added `_pace()` with per-session jitter before decisions, events, race starts, skill buys, and item handling.
**Status:** SUPERSEDED (by v3.0 — v3 ships its own delay/jitter system)

### 2026-06-27 — Item auto-buy cap priority in `_item_cap()`
**Commit:** `13b98c4` **File(s):** `career_bot/items.py`
**Context:** The UI's "Items to Auto Buy" caps were ignored by `_item_cap()`, which only checked `item_caps`. Changed priority order: `auto_buy_items` first, then `item_caps`, then `ITEM_INVENTORY_CAPS`.
**Status:** ACTIVE

### 2026-06-27 — Megaphone threshold tuning
**Commit:** `772cc41` **File(s):** `career_bot/items.py`
**Context:** 4-5 megaphones left unused per run. Lowered `_mant_cfg` defaults: small 11→8, medium 21→15, large 35→25.
**Status:** ACTIVE

### 2026-06-27 — Ankle weight inventory cap and usage threshold
**Commit:** `13b98c4`, `772cc41` **File(s):** `career_bot/items.py`
**Context:** Ankle weights over-bought (5 bought / 1 used per run) and rarely fired (base threshold 40 vs typical training scores of 20-35). Lowered inventory cap 3→2 and usage threshold 40→18.
**Status:** ACTIVE

### 2026-06-28 — Granular skip reasons in `_skip_buy()`
**Commit:** `074d66e` **File(s):** `career_bot/items.py`
**Context:** `_skip_buy()` returned `True`/`False`. The log viewer could only show "skip_buy" for every skipped item — no way to tell WHY. Changed to return string reason codes (`user_excluded`, `skip_wasteful`, `skip_notepad`, `skip_inv_cap`, `skip_mega_surplus`, `skip_anklet_cap`, `skip_cure_redundant`, `skip_budget`, `skip_pre_summer`, `skip_low_deck`, `skip_buff_used`). The caller passes the string through as `skip_reason` instead of collapsing to a generic label.
**Status:** ACTIVE — restored after v3.1

### 2026-06-28 — Manual aptitude overrides in solver
**Commit:** `7ed3bf4` **File(s):** `main.py`, `public/app.js`
**Context:** User sets Manual Start aptitudes in the UI (e.g. Mile: C), but "Solve Smart" ignored them — the solver always used master-data base aptitudes. Added `manual_aptitude_overrides` field to `TrackblazerPlanRequest` and wired the UI to send them separately via `solverManualAptitudes()`.
**Status:** SUPERSEDED (by v3.1 — upstream fixed root cause: UI now sends correct `trainee_name`/`trainee_id`, so solver reads the right trainee's base aptitudes from master data. Also, active UI moved to `public-v3/`, making the `public/app.js` change moot.)

### 2026-06-28 — Pre-race item logging to career report
**Commit:** `7ed3bf4` **File(s):** `career_bot/runner.py`
**Context:** Hammers and glow sticks used via `handle_pre_race()` were invisible in the career log. The turn snapshot was built before `_race()` was called, and `handle_pre_race()` wrote to `last_pre_race_use_selected` which was never captured. Added 16-line FORK block after `_reemit_item_use_debug(state)` that writes `bot_pre_race_use_selected` and `bot_pre_race_use_result` into the career report JSON.
**Status:** ACTIVE — restored after v3.1

### 2026-06-28 — Pre-climax hammer dump window
**Commit:** `ef3d93e` **File(s):** `career_bot/items.py`
**Context:** Artisan hammers stockpiled but never used on climax races (Masters preferred). No mechanism to spend Artisans before the climax window. Added dump window turns 65-73 (configurable via `trackblazer_hammer_dump_start_turn`). Invariant: Artisan hammers reach 0 before climax turn 74.
**Status:** ACTIVE

### 2026-06-28 — Log viewer created
**Commit:** `49d0eec` **File(s):** `log_viewer.html`
**Context:** Fork-only analytics tool. No upstream equivalent exists. Reads career log JSON and displays item usage, skip reasons, pre-race timeline, mood, coins.
**Status:** ACTIVE

### 2026-06-28 — AI summary export in log viewer
**Commit:** `dddc9da` **File(s):** `log_viewer.html`
**Context:** Added "Copy AI Summary" button that generates a structured text summary of the career run, suitable for pasting into an AI conversation for analysis.
**Status:** ACTIVE

### 2026-06-29 — Log viewer: clock, dump window analytics, cash-out tracking
**Commit:** `c97543d` **File(s):** `log_viewer.html`
**Context:** Added clock display, dump window visualization, and end-of-career cash-out tracking to the log viewer.
**Status:** ACTIVE

### 2026-06-29 — v3.1 upstream update applied
**Commit:** `d08a1a6`
**Context:** Applied upstream v3.1. Key additions: login persistence, per-distance strategy saves, loop run count, correct solver trainee, 53 shop exclusion items, event search by character, glow stick late/finale dump, Good-Luck Charm high-failure fix, per-occurrence race IDs. Three fork changes were silently reverted and required restoration (see next entry).
**Status:** N/A (upstream snapshot)

### 2026-06-29 — Restore fork data contracts after v3.1
**Commit:** `ea5eba3` **File(s):** `career_bot/items.py`, `career_bot/runner.py`
**Context:** v3.1 reverted three fork changes: (1) `_skip_buy()` returned `True`/`False` instead of string reasons, (2) caller collapsed all skip reasons to `"skip_buy"`, (3) pre-race item logging FORK block was deleted. All three restored because `log_viewer.html` depends on them.
**Status:** ACTIVE

---

## Collision Summary by Version

Quick-reference table for each upstream update. Detailed context is in the entries above.

### v3.1 (2026-06-29)

| Fork change | Outcome |
|---|---|
| `_skip_buy()` granular reasons | RESTORED — upstream reverted to `True`/`False` |
| `_skip_buy()` caller pass-through | RESTORED — upstream collapsed to `"skip_buy"` |
| Pre-race item logging (runner.py) | RESTORED — upstream deleted the FORK block |
| `manual_aptitude_overrides` (main.py) | SUPERSEDED — upstream fixed root cause |
| `public/app.js` manual overrides | SUPERSEDED — legacy UI replaced by v3 UI |
| `_pace()` pacing system | ALREADY GONE — removed during v3.0 merge |
| Megaphone/anklet thresholds | NO COLLISION |
| Hammer dump window | NO COLLISION |
| `_item_cap()` auto_buy priority | NO COLLISION |
| `log_viewer.html` | NO COLLISION |

### 2026-06-29 — Fix headless bypass ticket consumed before pre-load
**Commit:** `86aecd3` **File(s):** `main.py`
**Context:** `check_saved_auth()` creates a UmaClient and calls `c.login()` to test the headless bypass. This consumes the Steam session ticket. But `saved_cfg` (returned to the caller) still holds the old ticket. The startup pre-load then creates a second UmaClient with the stale ticket, causing 394 errors on `load/index`. Fixed by syncing the client's (possibly refreshed) ticket back into `saved_cfg` before returning it.
**Status:** ACTIVE

### 2026-06-29 — (nirio) fork tuning: skill, mood, charm, megaphone, anklet, whistle, cash-out
**Commit:** `112f0f3` **File(s):** `career_bot/trackblazer_rules.py`, `career_bot/items.py`, `career_bot/skills.py`
**Context:** Bot ended runs with 2362 SP unspent, mood 1 at climax, 322 leftover coins, 3 Good-Luck Charms, 4 megaphones, 3 whistles, and ankle weights unused. Added 16 configurable `nirio_*` keys to `mant_config` that lower late-game thresholds: skill buying forced at turn 60 (was 73), mood floor at motivation 2 after turn 50, charm/mega/anklet thresholds halved after turn 60-65, shop conservation lifted at turn 60, whistle usage from turn 60. All saved per-preset.
**Status:** ACTIVE

### 2026-06-29 — (nirio) race chain mood gating in strategy layer
**Commit:** `714bc1a` **File(s):** `career_bot/scenarios/mant_trackblazer.py`, `public-v3/modals.js`
**Context:** Bot continued optional race chains with mood 1 through turns 53-72, collapsing mood and training value before climax. Added two levels: soft break (prefer training over chain when mood <= floor after repair turn) and hard block (prevent all optional chains after critical turn 68 when mood <= floor). Both exempt mandatory races, year-end turns, and manual mode.
**Status:** ACTIVE

### 2026-06-29 — (nirio) UI section in Scenario Override Settings
**Commit:** `6f1a3d3` **File(s):** `public-v3/modals.js`
**Context:** Adds a "(NIRIO) FORK TUNING" section to the Scenario Overrides modal with sliders for all nirio_* config keys. Gives the user visibility and control over fork-specific behavior tuning.
**Status:** ACTIVE

### 2026-06-29 — Fix skill buying regression: nirio force blocked by enable gate
**Commit:** `c7aa149` **File(s):** `career_bot/skills.py`
**Context:** Second run still showed 0 skills bought with 2507 SP. Root cause: `enable_skill_point_check` gate (line 705) returned early before nirio force-turn logic could set `force=True`. Preset had skill checking disabled, silently blocking everything. Fixed by moving nirio force check and pre_finals_skill_dump check above the gate so they override it.
**Status:** ACTIVE

### 2026-06-29 — Dynamic MCH reserve for Climax races
**Commit:** `b4485ef` **File(s):** `career_bot/items.py`
**Context:** Run had only 2 Master Hammers at T73 despite reserve=3. T72 Arima consumed a Master when Artisan was unavailable. Replaced static `finale_reserve` with dynamic `protected_mch` that counts remaining Climax races (T74/T76/T78). Non-Climax G1s now prefer Artisan first; Master only if inventory exceeds dynamic reserve. Pre-conservation G1s also changed to prefer Artisan over Master.
**Status:** ACTIVE

### 2026-06-29 — Lower megaphone/anklet dump defaults
**Commit:** `fa8d027` **File(s):** `career_bot/trackblazer_rules.py`, `public-v3/modals.js`
**Context:** Run still ended with 3 megaphones and 3 anklets. Lowered defaults: mega turn 65→62, multiplier 50→35%; anklet turn 65→60, multiplier 50→30%. Anklets start earlier because they require matching training type.
**Status:** ACTIVE
