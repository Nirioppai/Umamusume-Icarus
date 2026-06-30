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
**Status:** ACTIVE | SUPERSEDED (by <what>) | INTEGRATED (after <version>)
```

For collision entries (where we chose between our fix and upstream's), add:

```
**Winner:** OURS | THEIRS | MERGED
**Evidence:** <why this version is better — run data, logic, test results>
**Integration:** <how the winning fix cooperates with upstream's logic>
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

### v3.2.1 (2026-06-29)

| Fork change | Winner | Integration |
|---|---|---|
| `_skip_buy()` granular reasons | OURS | Data contract — upstream has no equivalent |
| `_skip_buy()` caller pass-through | OURS | Data contract — log viewer depends on it |
| Pre-race item logging (runner.py) | OURS | Data contract — upstream only has live UI, not persisted JSON |
| Nirio skill forcing (skills.py) | MERGED | Nirio force runs before gate, then upstream's condition gating + graded tiers score downstream |
| Nirio mood floor / cupcake | OURS | Baseline: Climax Great. Without: Climax Bad, 13 bad turns. Integrated with upstream reserve |
| Nirio charm/mega/anklet dump | OURS | Slots into elif chains between upstream's ranges, additive |
| Nirio whistle dump | OURS | Uses min(upstream, nirio) — cooperative |
| Nirio cashout conservation | THEIRS | Upstream's `save_items_lategame` toggle must be respected. Removed bypass |
| Dynamic MCH reserve | MERGED | Uses upstream slider as max, dynamically reduces by remaining Climax races |
| Nirio race chain mood gating | OURS | Upstream has no mood-aware gating; max_races_in_row is planning-only |
| Skill hoard threshold | MERGED | Uses min(upstream 1500, nirio 1000) — more aggressive one wins |
| Pre-conservation G1 hammer | OURS | Artisan-first preserves Masters for Climax; evidence: 3 MCH at T73 vs 2 |
| Headless ticket sync (main.py) | OURS | Upstream still consumes ticket in check_saved_auth; pre-load uses stale one |
| `_item_cap()` auto_buy priority | OURS | auto_buy_items caps were silently ignored since v3.1 |
| Upstream skill condition gating | THEIRS | New feature, accepted wholesale, works with our forcing |
| Upstream graded skill tiers | THEIRS | New feature, accepted wholesale |
| Upstream clock retry 2507/205 | THEIRS | Upstream fixed root cause properly |
| Upstream live stat cap / route | THEIRS | New features, accepted wholesale |
| Upstream unsaved changes guard | THEIRS | New feature, works with nirio UI |

### v3.2.2 (2026-06-29)

| Fork change | Winner | Integration |
|---|---|---|
| `_skip_buy()` granular reasons | OURS | Data contract — upstream still returns True/False |
| `_skip_buy()` caller pass-through | OURS | Data contract — log viewer depends on it |
| Pre-race item logging (runner.py) | OURS | Data contract — upstream still only has live UI |
| Nirio skill forcing | MERGED | Nirio force + pre_finals both above gate; upstream's redesign scores downstream |
| Nirio mood floor / cupcake | OURS | Integrated with upstream's new kale-release (complementary) |
| Nirio charm dump (60-64) | OURS | Upstream has no 60-64 intermediate; their 65+ dump is accepted |
| Nirio mega dump turn/multiplier | **THEIRS** | **SUPERSEDED** — upstream drops score floor in dump mode, strictly more aggressive |
| Nirio anklet dump turn/multiplier | **THEIRS** | **SUPERSEDED** — upstream drops score floor in dump mode |
| Nirio cashout conservation | **THEIRS** | **SUPERSEDED** — already decided in v3.2.1 |
| Nirio whistle dump | OURS | min() of both turns — cooperative |
| Dynamic MCH reserve | MERGED | Uses upstream slider as max, dynamically reduces |
| Nirio race chain mood gating | OURS | Upstream still has no mood-aware gating |
| Skill hoard threshold | MERGED | min(upstream 1500, nirio 1000) |
| Pre-conservation G1 hammer | OURS | Artisan-first preserves Masters for Climax |
| Headless ticket sync | OURS | Upstream still consumes ticket in check_saved_auth |
| `_item_cap()` auto_buy priority | OURS | auto_buy_items still ignored by upstream |
| Upstream win probability | THEIRS | New feature, accepted wholesale |
| Upstream energy doctrine | THEIRS | New feature (suppress_energy, training-only) |
| Upstream summer train-over-rec | THEIRS | New feature, no conflict |
| Upstream cupcake kale-release | THEIRS | New feature, complementary with our mood floor |
| Upstream Discord toggles | THEIRS | New feature, accepted wholesale |

### v3.2.3 (2026-06-30)

Same collisions as v3.2.2 — no new fork changes superseded. One new upstream fix accepted.

| Fork change | Winner | Integration |
|---|---|---|
| All data contracts | OURS | Same as v3.2.2 |
| All nirio behavior (10 knobs) | OURS/MERGED | Same as v3.2.2 |
| MCH reserve, G1, skill, mood, charm | Same | Same integrations |
| **NEW: Whistle dump-late fix** | **THEIRS** | Whistle no longer blocks other item dumps in late game |
| Upstream CSS type-scale | THEIRS | UI-only, no fork conflict |
| Upstream Display panel | THEIRS | New feature, accepted |

### v3.2.4 + v3.2.5 (2026-06-30)

| Fork change | Winner | Integration |
|---|---|---|
| `_skip_buy()` granular reasons | OURS | Data contract — upstream reverted to `True`/`False` again |
| `_skip_buy()` caller pass-through | OURS | Data contract — upstream collapsed to `"skip_buy"` again |
| Pre-race logging FORK block (career report JSON) | OURS | Data contract — log_viewer.html reads `bot_pre_race_use_selected` from JSON |
| **NEW: `_patch_last_race_items` (live UI fix)** | **THEIRS** | Supersedes live-UI part of our FORK block; fixes lag-by-one on first Climax hammer |
| Runtime settings snapshot | OURS | log_viewer.html Active Settings section depends on it |
| Nirio skill forcing (skills.py) | MERGED | Nirio force before gate, pre_finals after gate |
| Nirio mood floor / cupcake | OURS | Evidence: Climax Awful without it |
| Nirio charm dump (60-64) | OURS | Upstream still has no 60-64 intermediate window |
| Nirio whistle dump turn | MERGED | `min(upstream_65, nirio_60)` — cooperative |
| Dynamic MCH reserve + G1 Artisan-first | MERGED | `protected_mch = min(nirio_reserve, remaining_climax)`; integrated with upstream total check |
| Nirio race chain mood gating | OURS | Upstream still has no mood-aware chain gating |
| Headless ticket sync (main.py) | OURS | Upstream still consumes ticket; pre-load uses stale one |
| `_item_cap()` auto_buy priority | OURS | auto_buy_items caps still ignored by upstream |
| **NEW: win-prob calibration** | **THEIRS** | Wholesale — read-only analytics, never affects play |
| **NEW: `public-v3/logview.html`** | **THEIRS** | Upstream's log viewer; coexists with our `log_viewer.html` |
| **NEW: career log API** | **THEIRS** | `/api/career/logs` + `/api/career/log`; complements our log viewer |
| All nirio UI sliders (modals.js) | OURS | Restored nirio section in Scenario Overrides |
| All nirio constants (trackblazer_rules.py) | OURS | Restored 13 DEFAULT_NIRIO_* constants |

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
**Status:** SUPERSEDED (by v3.2.2 — upstream drops score floor entirely in dump mode, strictly more aggressive)

### 2026-06-29 — v3.2.1 upstream update applied
**Commit:** `41f48f9`
**Context:** Applied upstream v3.2.1. Key additions: skill purchase redesign (condition gating, graded spreadsheet tiers, optimization target), clock retry 2507/205 fix, live stat cap, route awareness, race short mode, SSE event stream, unsaved changes guard, solver character match, unconditional manual career resume. All active fork changes were silently reverted and required restoration (see next entry).
**Status:** N/A (upstream snapshot)

### 2026-06-29 — Integrate fork fixes after v3.2.1
**Commit:** `17ee015` **File(s):** `career_bot/items.py`, `career_bot/runner.py`, `career_bot/skills.py`, `career_bot/trackblazer_rules.py`, `career_bot/scenarios/mant_trackblazer.py`, `public-v3/modals.js`, `main.py`
**Context:** v3.2.1 reverted all active fork changes. Integrated: data contracts, nirio tuning, MCH reserve, skill forcing, race chain gating. Upstream's new features (condition gating, graded tiers, live stat cap, SSE, unsaved guard) accepted. Five bypasses fixed to proper integrations (MCH uses upstream slider as max, cashout respects toggle, hoard uses min(), cupcake preserves reserve).
**Status:** ACTIVE

### 2026-06-29 — v3.2.2 upstream update applied
**Commit:** `06b81db`
**Context:** Applied upstream v3.2.2. Key additions: win probability calculator, energy doctrine (suppress_energy, training-only), summer training-over-recreation guard, cupcake kale-release, charm/mega/anklet dump more aggressive post-64 (drops score floor), Discord notification toggles + test, solver settings persistence (ssToggle/ssSelect), NPC core data expansion. All active fork changes silently reverted again.
**Status:** N/A (upstream snapshot)

### 2026-06-29 — Integrate fork fixes after v3.2.2
**Commit:** (pending) **File(s):** `career_bot/items.py`, `career_bot/runner.py`, `career_bot/skills.py`, `career_bot/trackblazer_rules.py`, `career_bot/scenarios/mant_trackblazer.py`, `public-v3/modals.js`, `main.py`
**Context:** v3.2.2 reverted all fork changes AND improved item dump logic. Anti-bias evaluation: upstream's new charm/mega/anklet dump (drops score floor in dump mode) is more aggressive than our nirio mega/anklet intermediates → those 3 nirio knobs SUPERSEDED. Nirio charm intermediate (60-64) still fills a gap upstream doesn't cover. Cashout already superseded in v3.2.1. Remaining 10 nirio knobs, data contracts, MCH reserve, skill forcing, mood gating, ticket sync, auto_buy all restored with proper integration.
**Winner:** MERGED — upstream's dump improvements accepted, nirio trimmed to 10 constants (from 16), non-redundant fixes re-applied.
**Status:** ACTIVE

### 2026-06-30 — v3.2.3 upstream update applied
**Commit:** `471e0c0`
**Context:** Applied upstream v3.2.3. Key additions: Display/Appearance panel (font size, body/heading/numeric fonts, accent theme), centralized CSS type-scale (all font sizes via variables), whistle dump-late short-circuit fix (whistle no longer blocks other item dumps in late game). All active fork changes silently reverted again.
**Status:** N/A (upstream snapshot)

### 2026-06-30 — (nirio) reverse-priority Climax hammer allocation
**Commit:** (pending) **File(s):** `career_bot/trackblazer_rules.py`, `career_bot/items.py`, `public-v3/modals.js`
**Context:** The flat "swing best hammer unconditionally" Climax logic was forward-greedy: T74 spent MCH first, T78 hoped one remained. The last Climax race has the highest stat value (T78 > T76 > T74). Replaced with reverse-priority allocation: protect `nirio_final_mch_required` (default 2) MCH for later races, so T74 only gets a Master Hammer if 3+ are owned. Added `nirio_final_artisan_reserve` (default 1) for the same Artisan fallback protection. With defaults: T74 uses Artisan if tight; T76 uses MCH if 2+ owned; T78 always gets the best available. Two new sliders added to the nirio UI section.
**Status:** ACTIVE

### 2026-06-30 — Log viewer: fix leftover item source of truth
**Commit:** (pending) **File(s):** `log_viewer.html`
**Context:** Per-item leftover count (bought − used ledger) disagreed with final_inventory snapshot. The ledger reported leftover manuals, carrots, and scrolls that were not present in final_inventory or confirmed in-game. Root cause: usage events can be incomplete or double-counted, causing ledger drift. Fixed by preferring `last.inventory` total as the authoritative leftover count in the overview card, AI summary export, dump window assessment, and cash-out analysis. Ledger columns retained for per-item economy analysis. Added ⚠ accounting mismatch warning when the two sources differ by more than 2 items.
**Status:** ACTIVE

### 2026-06-30 — Integrate fork fixes after v3.2.3
**Commit:** `91f7650` **File(s):** `career_bot/items.py`, `career_bot/runner.py`, `career_bot/skills.py`, `career_bot/trackblazer_rules.py`, `career_bot/scenarios/mant_trackblazer.py`, `public-v3/modals.js`, `main.py`
**Context:** v3.2.3 is primarily a UI/display overhaul (CSS type-scale). One new upstream behavior fix: whistle dump-late short-circuit (accepted). All fork changes identical to v3.2.2 integration re-applied. No new superseded knobs.
**Winner:** MERGED — upstream's whistle dump-late fix accepted, all 10 nirio knobs + data contracts + integrations re-applied.
**Status:** ACTIVE

### 2026-06-30 — v3.2.4 + v3.2.5 upstream update applied
**Commit:** `3195b8c`
**Context:** Applied upstream v3.2.4/v3.2.5 (shipped as one commit). Key behavioral additions: `_patch_last_race_items()` — live UI fix that patches the pre-race items on the action_history row (fixes the lag-by-one issue where first climax hammer was invisible in the live UI); opponent-aware win-probability self-calibration (`win_prob_calibration.py`); race field capture (`race_scenario.py`) for calibration. Career log serving API (`/api/career/logs`, `/api/career/log`). Key visual additions: `public-v3/logview.html` (upstream's own log viewer), dashboard stat charts, 78-turn career heatmap, race replay, attribute radar, head-to-head compare, cockpit touches. All active fork changes silently reverted again.
**Status:** N/A (upstream snapshot)

### 2026-06-30 — Integrate fork fixes after v3.2.5
**Commit:** (pending) **File(s):** `career_bot/items.py`, `career_bot/runner.py`, `career_bot/skills.py`, `career_bot/trackblazer_rules.py`, `career_bot/scenarios/mant_trackblazer.py`, `public-v3/modals.js`, `main.py`, `CLAUDE.md`, `UPDATING.md`
**Context:** v3.2.5 reverted all fork changes AND added `_patch_last_race_items()` which supersedes the live-UI portion of our pre-race logging FORK block. Upstream's new career log API also complements (but does not replace) our log_viewer.html. CHANGELOG.md added to the audit process per updated CLAUDE.md. Anti-bias evaluation: `_patch_last_race_items` is BETTER than our FORK block for live UI → accept theirs AND keep ours (they serve different outputs: live action_history vs career report JSON). All 10 nirio knobs, data contracts, MCH reserve + G1 Artisan-first, skill forcing, mood gating, ticket sync, auto_buy cap priority all restored with proper integration.
**Winner:** MERGED — upstream's live UI fix + win-prob calibration + logview.html accepted wholesale. Fork data contracts, nirio tuning, and integrations re-applied.
**Status:** ACTIVE
