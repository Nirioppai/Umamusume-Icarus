# CLAUDE.md — Icarus Fork Merge Guide

This file documents all modifications made to the Icarus codebase since v2.0 (`1d47869`).
When upstream updates arrive, use this as the authoritative guide for merge conflict resolution.

## Coding Rules for This Project

1. **Every change to bot logic must include a one-line comment explaining WHY** — not what the code does, but why it was changed from the original. Use the format: `# FORK: <reason>` for Python, `// FORK: <reason>` for JS.
2. **Never silently revert a fork change during a merge.** If upstream rewrites a function we modified, compare both versions against the problem statement documented below before choosing.
3. **Threshold/constant changes are user-tunable.** If upstream changes the same constant, prefer the value that is closer to the user's measured need (documented below), not the higher or lower one by default.
4. **Log viewer changes are additive.** `log_viewer.html` is a fork-only file. Upstream does not ship it. Never delete it during merges.
5. **The `public/app.js` UI change (manual aptitude overrides) is a bugfix, not a feature.** It must survive any upstream rewrite of `getTrackblazerOptions()`.

---

## File-by-File Change Registry

### `main.py` — Smart Race Solver aptitude override fix

**Problem:** The user sets Manual Start aptitudes in the UI (e.g., Mile: C), but clicking "Solve Smart" ignored them entirely. The solver always used master-data base aptitudes.

**Root cause:** `_trackblazer_profile_aptitudes()` line ~3625 had `if not aptitudes and req.aptitudes:` — the UI-supplied aptitudes were a fallback, not an override. Since every known trainee has a master-data profile, the UI values were never used.

**Fix:** Added `manual_aptitude_overrides` field to `TrackblazerPlanRequest`. The backend now applies ONLY the specific dimensions the user manually changed (e.g., just Mile), on top of the master-data base. The full `req.aptitudes` (which includes spark bonuses for ALL dimensions) is still used as a fallback for unknown trainees.

**Merge guidance:** If upstream rewrites `_trackblazer_profile_aptitudes`, ensure the new version still accepts `manual_aptitude_overrides` and overlays them on top of base profile data. The key invariant: **user manual overrides must beat master-data defaults, but spark-boosted values must NOT replace un-touched dimensions.**

### `public/app.js` — Sends manual overrides separately

**Change:** `getTrackblazerOptions()` now sends `manual_aptitude_overrides: { ...solverManualAptitudes(current) }` alongside the existing `aptitudes` field.

**Merge guidance:** If upstream rewrites `getTrackblazerOptions()`, add this one line back. The `solverManualAptitudes(current)` function already exists in the UI code.

### `career_bot/items.py` — Item usage and buying improvements

#### 1. Granular skip reasons in `_skip_buy()`
**Problem:** `_skip_buy()` returned `True`/`False`. The log viewer could only show "skip_buy" for every skipped item — no way to tell WHY.
**Fix:** Returns string reasons: `"auto_buy_cap"`, `"user_excluded"`, `"skip_wasteful"`, `"skip_notepad"`, `"skip_inv_cap"`, `"skip_mega_surplus"`, `"skip_anklet_cap"`, `"skip_cure_redundant"`, `"skip_budget"`, `"skip_pre_summer"`, `"skip_low_deck"`, `"skip_buff_used"`, or `None` (buy it).
**Merge guidance:** If upstream rewrites `_skip_buy()`, convert their boolean returns to string reasons. The log viewer depends on these strings for the skip reason breakdown.

#### 2. `_item_cap()` respects `auto_buy_items`
**Problem:** The UI's "Items to Auto Buy" caps were ignored by `_item_cap()`, which only checked `item_caps`.
**Fix:** `_item_cap()` now checks `auto_buy_items` first, then `item_caps`, then `ITEM_INVENTORY_CAPS`.
**Merge guidance:** Keep this priority order. The auto_buy feature is a user-facing UI control.

#### 3. Ankle weight inventory cap: 3 → 2
**Problem:** 5 bought / 1 used per run. Over-buying with no usage.
**Fix:** `ITEM_INVENTORY_CAPS` for ankle weights lowered from 3 to 2. Note: user's preset `auto_buy_items` may override this to 4 — the user was advised to lower that too.
**Merge guidance:** Upstream may change this. Prefer whichever value matches measured usage (typically 1-2 per run).

#### 4. Ankle weight usage threshold: 40 → 18
**Problem:** Base threshold of 40 was too high; most training turns score 20-35, so anklets rarely fired.
**Fix:** Lowered to 18 with looser summer (0.75) and late-game (0.82) multipliers.
**Merge guidance:** This is the most aggressive tuning change. If upstream adjusts `_anklet_target()`, compare their threshold against actual training scores in logs. The original 40 left 3-4 anklets unused per run.

#### 5. Megaphone thresholds lowered
**Problem:** Megaphones left over at end of career (4-5 unused).
**Fix:** `_mant_cfg` defaults changed: small 11→8, medium 21→15, large 35→25.
**Note:** The `_megaphone_target()` fallback values (`or 21`/`or 31`/`or 45`) were NOT changed — they only fire if cfg is empty, which never happens since `_mant_cfg` always sets defaults.
**Merge guidance:** If upstream changes megaphone thresholds, pick whichever results in fewer leftover megaphones per run.

#### 6. Pre-climax hammer dump window
**Problem:** Artisan hammers stockpiled but never used on climax races (Masters preferred). No mechanism to spend Artisans before the climax window.
**Fix:** New dump window (turns 65-73, configurable via `trackblazer_hammer_dump_start_turn`). During this window, Artisan hammers are used on ANY G1/G2/G3 race. Excess Masters (above finale reserve) are spent on G1s only.
**Merge guidance:** If upstream adds their own dump logic, compare strategies. Key invariant: **Artisan hammers should reach 0 before climax turn 74, because climax races always prefer Masters.**

### `career_bot/runner.py` — Pacing and pre-race logging

#### 1. Pacing system (`_pace()`, `dna_sleep` calls)
**Problem:** Bot actions were instant, making the request pattern machine-like.
**Fix:** Added `_pace()` method with per-session `pace_scalar` (0.8-1.3). Calls inserted before decisions, events, race starts, skill buys, and item handling.
**Merge guidance:** If upstream adds their own pacing/delay system, prefer theirs (they know the API rate limits). Remove our `_pace()` calls to avoid double-sleeping.

#### 2. Pre-race item usage logging
**Problem:** Hammers and glow sticks used via `handle_pre_race()` were invisible in the career log. The turn snapshot was built before `_race()` was called, and `handle_pre_race()` wrote to `last_pre_race_use_selected` which was never captured.
**Fix:** After `handle_pre_race()` in `_race()`, the code finds the matching turn entry in `self.report["turns"]` and attaches `bot_pre_race_use_selected`. Falls back to the last turn with stats if no exact match exists (prevents creating sparse turn entries that break the stats display).
**Merge guidance:** If upstream fixes pre-race logging differently, prefer theirs. If they don't address it, keep this fix. The key invariant: **pre-race item usage must appear in the career log JSON so the log viewer can display it.**

### `career_bot/trackblazer_rules.py` — Constants unchanged from user session

All constants in this file remain at their original v2.0 values. The user's preset overrides (via Scenario Override Settings in the UI) take precedence at runtime. No merge conflicts expected.

### `log_viewer.html` — Fork-only file (not in upstream)

This file is entirely authored by the fork. Upstream does not ship a log viewer.

**Key features that depend on bot-side changes:**
- `bot_pre_race_use_selected` — read from career log JSON, depends on the runner.py logging fix above
- Granular skip reasons — depends on `_skip_buy()` returning strings, not booleans
- `fmtItem()` — display name formatter (e.g., "Master Cleat Hammer" → "Hammer (Master Cleat)") — purely client-side, no bot dependency
- Mood summary, bought/used comparison, leftover coins, pre-race timeline — purely client-side analytics

**Merge guidance:** Never delete this file. If upstream adds their own log viewer, evaluate merging features.

---

## Merge Decision Framework

When upstream updates a function we've modified, evaluate in this order:

1. **Does upstream's version fix the same bug we fixed?** → Use upstream's version (cleaner, maintained).
2. **Does upstream's version break our fix?** → Keep our version, file an issue upstream.
3. **Are both versions addressing different problems?** → Merge both: apply upstream's structural changes, then re-apply our specific fix on top.
4. **Is it a threshold/constant change?** → Compare against the user's measured item usage data (see log viewer reports). Pick the value that results in fewer leftover items per run.
5. **Is it a new feature we don't have?** → Accept upstream's version wholesale. Then verify our fixes still apply.

## Files Safe to Accept Upstream Wholesale

These files have NO fork modifications to the bot logic:
- `career_bot/skills.py`
- `career_bot/races.py`
- `career_bot/scenarios/mant_trackblazer.py`
- `career_bot/report.py`
- `career_bot/config_store.py`
- `career_bot/training_scorer.py`
- `career_bot/calibration.py`
- All files under `data/` (except fork-added `data/event_outcomes.json` updates)
- All files under `tests/`
- `public/styles.css`
- `public/index.html`
