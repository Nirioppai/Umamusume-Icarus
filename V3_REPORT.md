# V3 Branch Analysis Report

**Comparing:** `master` → `v3-raw`
**Purpose:** Cherry-pick guide for `master-v3-merge` branch
**Date:** 2026-06-28

---

## Table of Contents

1. [New Features in v3-raw](#1-new-features-in-v3-raw)
2. [Improved Features in v3-raw](#2-improved-features-in-v3-raw)
3. [Master Features Removed in v3-raw](#3-master-features-removed-in-v3-raw)
4. [Cherry-Pick Recommendations](#4-cherry-pick-recommendations)
5. [File-Level Change Index](#5-file-level-change-index)
6. [Summary Statistics](#6-summary-statistics)

---

## 1. New Features in v3-raw

### 1.1 New UI: `public-v3/` (Complete Rewrite)

v3-raw ships an entirely new frontend in `public-v3/`. The old UI (`public/`) is preserved at `/legacy/`. v3 is now the default at `/`.

**New v3 UI files:**
- `public-v3/index.html` — Main dashboard (dark "cockpit" aesthetic, left status rail, tab strip nav)
- `public-v3/core.js` — Shared framework (938 lines): `Icarus.api()`, nav rail, TP/carrots/gold/clocks pills
- `public-v3/app.js` — Main app logic (736 lines): vitals panel, action log feed, decision reasoning, stat chart
- `public-v3/modals.js` — Settings modals (1104 lines): training/racing/scenario sub-modals
- `public-v3/setup.html` / `setup.js` — Setup wizard (1196 lines): team slots, presets, race planner
- `public-v3/history.html` / `history.js` — Career history viewer
- `public-v3/events.html` / `events.js` — Event catalog browser
- `public-v3/diag.html` / `diag.js` — Diagnostics panel
- `public-v3/accounts.html` / `accounts.js` — Multi-account manager
- `public-v3/help.html` — Help documentation (1124 lines)
- `public-v3/styles.css` — Full stylesheet (1009 lines)
- `public-v3/model-test/` — 3D model viewer prototype (PMX model of Seiun Sky + textures)

### 1.2 New API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/character-profile/roster` | Full trainee roster for character picker |
| `GET /api/character-profile/colors` | Per-card UI accent colors for theming |
| `GET /api/trackblazer/races` | Race calendar for manual race picker |
| `GET /api/card-art/{image_name}` | 512x512 trainee illustrations with fallback chain |
| `GET /api/logs/export` | Zip all career logs with re-redaction for sharing |
| `POST /api/career/runner/skill_intercept` | DEV-ONLY: web-based skill-buy intercept toggle |
| `POST /api/career/runner/skill_decision` | DEV-ONLY: submit skill purchase decision from web UI |

### 1.3 Late-Game Item Dump System (`items.py`)

A comprehensive time-windowed item spending policy controlled by `save_items_lategame` config:
- **Turns 60-64 (late summer):** Fire items on any non-zero training, thresholds drop to 0
- **Turns 65-70 (late spend):** Stop conserving, spend remaining stock
- **Turns >= 71 (late final):** Fire only when training raises highest-priority non-capped stat

Affects: charms, megaphones, anklets, cupcakes, energy items, whistles. Replaces master's approach of globally-lowered thresholds with structured dump windows.

### 1.4 Group Outing Stall Detector (`runner.py`, Sirius/Throne)

Detects when a group outing command is a server no-op (same turn returns, no error). If the same outing fires twice on the same turn, it blocks either the card outing or scheduled outing and forces a re-decide. Bad group outing errors no longer kill the career.

### 1.5 Per-Race Running Style Overrides (`runner.py`)

Preset-configurable per-race style overrides via `mant_config.per_race_style_overrides`. Matches by race name or `program_id`, with optional `stamina_below` gate. Only fires when a concrete base style (1-4) is configured.

### 1.6 Epithet (Set-Bonus) Completion Announcements (`runner.py`)

Announces set bonuses the moment their final race is won, showing the reward (e.g., "Set bonus earned: Classic Triple Crown (2 random stats +15)"). Each epithet reported once, only for reward-carrying epithets.

### 1.7 Consecutive Race Energy Management (`items.py`)

Pre-race energy items only used at 0 energy when the race is 2nd or 3rd in a consecutive chain (1st race has low punishment, 4th+ has capped punishment). Uses `_smallest_sufficient_prerace_energy` that prefers Energy Drink MAX (+5) over Vita items.

### 1.8 Rainbow Partner Gating for Megaphones (`items.py`)

Megaphones now only fire during summer camp, on turns with 2+ rainbow partners (bond >= 80), or during dump/inventory pressure windows — preventing year-round misfires on mediocre training.

### 1.9 Cupcake Type Differentiation (`items.py`)

`kind="plain"` picks Plain Cupcake first (for kale mood offset), while Berry-Sweet-first order is used for mood recovery. Prevents burning Berry Sweet Cupcakes on kale offsets.

### 1.10 Career Log Slimming & Redaction (`report.py`)

- **API call slimming:** Career logs were ~50MB; each call is now projected down to metadata + essential response keys. Shrinks logs ~95%.
- **Sensitive data redaction:** Device IDs, IP addresses, Steam IDs, auth keys recursively scrubbed to `[REDACTED]`.
- **Build version stamping:** Every career log includes the build label from `CHANGELOG.md`.

### 1.11 Planned-Skill Event Preference (`events.py`)

Events now check if a choice hints a skill the user explicitly planned to buy (`forced_skills` / `manual_skill_tiers`). Matching choices get a +30 bonus. Surfaced in reasoning as `skill_hint_planned:<name>`.

### 1.12 Canonical Race Name Matching (`trackblazer.py`)

Fixes "Japanese Derby (Tokyo Yushun)" vs "Tokyo Yushun (Japanese Derby)" alias problem. Both orderings collapse to one canonical key by sorting base + parenthetical halves. Fixes Triple Crown forcing and epithet matching.

### 1.13 Sirius/Throne Mode Support (`mant_trackblazer.py`)

- Scheduled group outings (Mode A), free group outings (Mode B)
- Junior bond focus for group-card decks (turns <= 11, prefer facilities with most group-card partners)

### 1.14 Rainbow Attenuation (`mant_trackblazer.py`)

Rainbow training bonus is attenuated by how full the trained stat already is. Near-capped stats get reduced rainbow multiplier so the engine stops chasing rainbows on finished stats.

### 1.15 Bond Rework (`mant_trackblazer.py`)

- `REL_VALUE_ORANGE` raised from 0.0 to 0.4 (low-bond partners now scored, enabling bond-rushing in junior)
- Bond values now per-preset configurable via `bond_value_orange/green/blue` and `bond_weight`

### 1.16 Rival Overwrite Support (`races.py`)

In Trackblazer manual mode, when the game offers a rival race that matches an overwrite entry instead of the main race, the planner runs the rival race. Only place manual mode deviates from strict race list.

### 1.17 Navbar Clock/Retry Controls (`runner.py`)

- `clocks_g1_debut_only`: Only Debut, G1, and CLIMAX finale races may use retries
- `max_retries_per_race`: Runtime override from navbar (-1 = default, 0 = no retries)

### 1.18 Finalize Single Runs (`runner.py`)

When ON, single (non-loop) runs play out the final URA turn and finalize the career instead of self-terminating at turn 77, so the game-side career closes cleanly.

### 1.19 Manager Restart Budget (`manager.py`)

`MAX_RESTARTS_PER_HOUR = 10` ceiling. A child that exhausts its restart budget is marked `failed` and left dead, preventing infinite restart loops. Invalid JSON handling backs up bad config files instead of crashing.

### 1.20 New Skill Config Keys (`config_store.py`)

- `manual_skill_tiers_dont_spend_extra` — manual tiers buy ONLY listed skills
- `skill_stop_after_recommended` — stop buying after recommended list exhausted
- `skill_manual_auto_fallback` — fallback to auto when manual list empty

### 1.21 Skill Purchase Retry & Verification (`skills.py`)

Career-persistent owned skill tracking (`_acquired_skill_ids` set) solves the "Fast-Paced / 200542 re-buy bug" where skills rotated out of the game's partial `skill_array` view and got re-bought. The old fire-and-forget `gain_skills()` call is replaced with a 3-attempt retry loop:
- `_reload_state()` refreshes single-mode state before retrying
- `_confirm_purchases()` verifies which skills the server actually granted
- Only records "ok" on confirmed purchase; prevents silent 205/208 failures

### 1.22 Distance Mismatch Skill Filter (`skills.py`)

Hard filter (`_skill_distance_mismatch()`) prevents auto-buying distance-exclusive skills outside the trainee's primary/secondary distances (e.g., a Long-only skill on a Miler).

### 1.23 Stop-After-Recommended Skill Gate (`skills.py`)

When enabled, once the trainee's recommended/best skills (preferred + community SS/S tier) are all owned, the bot stops generating candidates so SP is not dumped into marginal skills. Bypassed pre-finals.

### 1.24 DEV-ONLY Web Skill Intercept (`skills.py`)

When enabled, blocks skill-buy flow until user confirms/edits/skips via browser popup. Builds full catalog of buyable skills with names + costs. Handles "skip", "confirm" (user-chosen IDs), and "proceed" (keep bot picks).

### 1.25 Team Sirius/Throne Group Outing System (`mant.py`)

Full recreation outing scheduling for Team Sirius (30081) and Heirs to the Throne (30067) group support cards:
- Hardcoded `SIRIUS_THRONE_RECREATION_SCHEDULE` mapping turns to character outings
- **Mode A ("scheduled"):** Goal-driven — fires earliest scheduled step that is due/available with prerequisite checks
- **Mode B ("free"):** Opportunistic — fires group outings with next available unlocked character
- **"off":** Disabled. Auto-detection defaults to "scheduled" if group cards are in deck
- Blackout turns during summer camp (turns 36-40, 60-64)
- Recreation debug dump writes outing state to `bot_logs/recreation_debug_t<N>.json`

### 1.26 Summer All-Out Energy Rescue (`mant.py`)

For group-card decks in scheduled mode, any positive-gain Lv5 summer camp turn is worth rescuing (not just rainbow/high-score turns). Controlled by `summer_all_out` config.

### 1.27 Deck Sanitization (`uma_api/deck_sanitize.py`)

New module handles duplicate friend cards in owned support list (not just over-count). Diagnostic logging of exact deck/friend payload sent to game.

### 1.28 Career Start Recovery (`career_bot/career_start_recovery.py`)

Validates and 0-safe coerces a live `career_status` for resuming active careers. Self-heals to fresh start instead of crashing on stale/incomplete career data.

### 1.29 Year-End Energy Waste Prevention (`trackblazer_rules.py`)

New constants distinguish rest-guard exemptions from energy-waste turns. Don't spend recovery items on the last turn of a year (turns 24, 48, 72).

### 1.30 Server Rejection Tracking (`runner.py`)

Rolling 10-minute window of server-side rejections (208/5xx/394) exposed as `status["recent_server_rejects"]` so the dashboard can distinguish throttling from clean idle states.

### 1.31 HWID Robustness (`uma_api/client.py`)

3-tier fallback for system identity: (1) volatile BIOS hive, (2) persistent `SystemInformation` key, (3) WMI via PowerShell. Fixes startup failures on newer Windows builds where the volatile BIOS key is absent.

### 1.32 Card Art Assets (`data/card_art/`)

~90 new 512x512 standing trainee illustration PNGs added for the v3 UI character picker.

### 1.33 Updated Image Assets (`data/images/`)

All existing card/support images upgraded to higher resolution versions (~400-500 files).

---

## 2. Improved Features in v3-raw

### 2.1 Resilient Startup (`main.py`)

- `master.mdb` generation moved from module scope to async `_lifespan()` — makes `import main` side-effect-free for testing
- All JSON data file loads wrapped in try/except with `STARTUP_WARNINGS` collection — server starts even with corrupt data

### 2.2 Event System Overhaul (`main.py`, `events.py`)

- Event source changed from `event_effects_scraped.json` to `event_effects.json`
- Name-based index (`by_name`) for matching by event name, not just story_id
- Full event catalog populated even before a career has run
- Added `category` field ("support_card" vs "story") and `choice_select_indices`

### 2.3 Guest Parent Bug Fix (`main.py`)

`normalize_guest_parents()` gets `strict` parameter. When `strict=True`, skips broad summary scan and heuristic discovery, preventing random umas from being misclassified as guest parents.

### 2.4 Career Resume Self-Healing (`main.py`)

Uses `resume_career_fields()` from `career_start_recovery`. If resume fails (stale career, missing chara_info, int(None) crashes), self-heals by clearing state and falling through to fresh start.

### 2.5 Multi-Account Health Monitoring (`main.py`)

- Health probe timeout raised 1.5s → 6s with TCP probe fallback
- Live instance identifies itself in roster (never falsely reports itself as offline)
- Auto-inserts itself if not in roster, adds `runs`/`fans` stats

### 2.6 Hammer Conservation Rewrite (`items.py`)

Replaced simple dump window with unified `finale_reserve` system:
- Banks exactly N hammers for climax races, spending surplus Artisan first
- G1 always considers Artisan; G2/G3 never spend Masters
- Legacy `trackblazer_hammer_finale_reserve` honored as fallback

### 2.7 Anklet Logic Rework (`items.py`)

- Base threshold reverted from fork's 18 to 30 (closer to original 40)
- 3-window late-game policy replaces aggressive global threshold
- Summer camp multipliers refined (0.80 for first camp, zero-threshold for turns 60-64)

### 2.8 Item Pre-Race Visibility (`runner.py`)

Pre-race items (hammers, glow sticks) now appear in both reasoning panel and v3 monitor cards. The 1-turn debug lag is fixed.

### 2.9 Retry Policy Changes (`runner.py`)

- Default `retry_race_grades` expanded from `["G1"]` to `["G1", "CLIMAX"]`
- Grade gate now applies to ALL races including mandatory ones
- `clocks_g1_debut_only` adds strict override layer

### 2.10 Finale Bonus Gating (`mant_trackblazer.py`)

Finale stat buffer now applied only when `turn >= 73`, not career-wide. Previously it shrank effective cap to ~1055 from turn 0.

### 2.11 Milestone Slider Fix (`mant_trackblazer.py`)

Now reads `classic_year_milestone_pct` / `senior_year_milestone_pct` (what the UI writes) instead of only `classic_milestone_pct` / `senior_milestone_pct` (what the UI never wrote).

### 2.12 Aptitude Floor Fix (`mant_trackblazer.py`)

The `_solver_aptitude_floor()` call was on `self.ref` (MantStrategy, which has no such method) — always raised `AttributeError` and fell back to 6. Now correctly calls `rp._solver_aptitude_floor()`.

### 2.13 Berry Sweet Cupcake Integration (`mant_trackblazer.py`)

When a cupcake is available and energy is low enough for the item layer to queue it, skip Recreation and let the training turn spend the cupcake for mood recovery instead.

### 2.14 Async Snapshot Reading (`main.py`)

`latest_career_snapshot()` moved to `asyncio.to_thread()` so large snapshot files don't block the event loop.

### 2.15 Whistle Policy Tightened (`items.py`)

Whistles restricted to summer camp turns and late-game (>= turn 65). At turn >= 65, uses separate `late_whistle_lackluster_threshold` (default 30).

### 2.16 Coin Reserve Reduced (`items.py`)

Default `trackblazer_finale_coin_reserve` lowered 175 → 150. In dump mode, further capped to 60 (just enough for one Master Cleat Hammer).

### 2.17 Skill Loading Robustness (`skills.py`)

`_load()` initializes all table attributes up-front before parsing; per-row errors skip individual rows instead of aborting the entire 8000-row skill table. Records `load_error` for diagnostics.

### 2.18 Blacklist Improvements (`skills.py`)

Now reads from BOTH `learn_skill_blacklist` (legacy) and `skill_strategy.blacklist` (Configure Skills UI). Accepts skill IDs as well as names.

### 2.19 Manual Skill Tiers Now First-Class (`skills.py`)

No longer gated on `enable_skill_point_check_plan` being off (which silently ignored the user's tier list). Manual tiers are always honored when populated, with explicit manual-vs-auto-fallback toggle.

### 2.20 Legacy Engine Removal (`mant.py`)

The entire Classic/Legacy training scorer (800+ lines) has been deleted from `mant.py`. This includes `_best_command()`, `_score_command()`, all scoring sub-systems (`_rainbow_bonus`, `_target_pressure_multiplier`, `_starved_stat_multiplier`, `_stat_priority_multiplier`, `_wit_balance_multiplier`, etc.), the stat target system, and all legacy decision support helpers. The `decide()` method now always delegates to `self._trackblazer_core().decide()`. Legacy mode values ("legacy", "classic", "android") are accepted but all route to Trackblazer.

### 2.21 Legacy UI Updates (`public/app.js`)

The existing `public/` UI received significant updates in v3-raw:
- **Library tab bar** replaces accordion sections
- **Event choices category filter** — "Story Events" vs "Support Card Events" tabs
- **Per-race style overrides** UI section
- **Rainbow attenuation controls** (floor slider, toggle)
- **New shop/item settings** — coin reserve, BBQ threshold, save items for late game, late whistle threshold
- **Export logs button** downloads career logs as zip
- **Beta build badge** shown for beta versions
- **Compact gold display** ("1.1M" / "100k" format)
- **Request abort timeout** (15s) and live-status poll self-healing
- **Server throttle indicator** in footer
- **Auto-persist manual race picks** (no separate "Apply Manual" click)
- **Removed:** Event Outcome KB UI, auto-buy items UI, character profile scorer mode, stat priority/targets editor, `manual_aptitude_overrides` in solver payload

---

## 3. Master Features Removed in v3-raw

### 3.1 Entire Pacing System (REMOVED)

**Master has:** `_pace()` method with per-session `pace_scalar` (0.8-1.3), calls before decisions/events/races/skills/items, random 3% chance of 5-30s sleep, `GateKeeper` proxy class, `_BASE_DELAYS` table (24 endpoints), `simulate_delay()`, `simulate_turn_delay()`.

**v3-raw:** All removed. Bot runs at wire speed. The delay.py file retains only `dna_sleep()` utilities.

**Impact:** The pacing system was added to make request patterns less machine-like. v3-raw relies on the server-side `attach_turn_delay` / `wait_for_game_turn_delay` in `main.py` instead.

### 3.2 Training Scorer / Character Profile System (REMOVED)

**Master has:** `career_bot/training_scorer.py` (832 lines) — standalone training scorer with ~30 tunables, `TrainingScorerConfig`, `score_trainings()`, stat efficiency/relationship/rainbow/urgency component functions. Character profiles with `training_scorer_overrides` and `training_scorer_mode`.

**v3-raw:** Entirely deleted. The Trackblazer engine in `mant_trackblazer.py` is the sole scorer. All scorer status fields, reasoning display code, and profile mode endpoints removed.

### 3.3 Event Outcome Knowledge Base (REMOVED)

**Master has:** `career_bot/event_outcomes.py` (571 lines), `data/event_outcomes.json` (14K lines), `data/dumper_outcomes_import.json` (1.2K lines), native event capture system, import/export endpoints, `_capture_event_outcome()` method.

**v3-raw:** All removed. Event system now uses `event_effects.json` (scraped DB) + inline rewards from live API as sole source of truth.

### 3.4 Policy Guards (REMOVED)

**Master has:** `career_bot/policy_guards.py` (248 lines) — safety rails for live AI policy adjustments with bounded adjustment caps, minimum sample gates, KL-divergence drift detection.

**v3-raw:** Deleted. Part of the broader AI policy adjustment subsystem removal.

### 3.5 Fork-Specific Item Tuning (REVERTED)

| Tuning | Master (Fork) | v3-raw |
|--------|---------------|--------|
| Anklet inventory cap | 2 per type | 3 per type (reverted) |
| Anklet firing threshold | 18 | 30 |
| Megaphone thresholds | 8 / 15 / 25 | 11 / 21 / 35 (reverted) |
| `auto_buy_items` priority in `_item_cap()` | First priority | Removed |
| `auto_buy_items` check in `_skip_buy()` | Present | Removed |

**Why acceptable:** v3-raw replaces global threshold lowering with structured late-game dump windows (§1.3).

### 3.6 Manual Aptitude Overrides (REVERTED)

**Master has:** `manual_aptitude_overrides` field in `TrackblazerPlanRequest`, backend overlays only user-changed dimensions on top of master-data base.

**v3-raw:** Reverted to original fallback pattern (`if not aptitudes and req.aptitudes`).

**Impact:** The fork's aptitude override fix (documented in CLAUDE.md) is lost. This was a bugfix, not a feature.

### 3.7 Fork's Hammer Dump Window (REPLACED)

**Master has:** Explicit pre-climax dump window (turns 65-73) via `trackblazer_hammer_dump_start_turn`, spending Artisan hammers on any G1/G2/G3 race.

**v3-raw:** Replaced by surplus-based conservation system with per-grade Artisan gates.

### 3.8 Fork's Skip Reason Strings (STATUS UNCLEAR)

**Master has:** `_skip_buy()` returns string reasons like `"auto_buy_cap"`, `"skip_budget"`, etc.

**v3-raw:** The `_skip_buy()` was heavily rewritten. Need to verify if string returns are preserved (the log viewer depends on these).

### 3.9 Removed Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/events/outcome-kb` | Event outcome KB summary |
| `GET /api/events/native-capture` | Native event capture status |
| `POST /api/events/native-capture` | Toggle native event capture |
| `POST /api/events/outcome-kb/import` | Import event outcomes |
| `POST /api/character-profile/mode` | Toggle training scorer mode |
| `POST /api/character-profile/training-targets` | Edit per-distance stat targets |

### 3.10 Removed Files

| File | Lines | Purpose |
|------|-------|---------|
| `career_bot/training_scorer.py` | 832 | Standalone training scorer |
| `career_bot/event_outcomes.py` | 571 | Event outcome KB |
| `career_bot/policy_guards.py` | 248 | AI policy safety rails |
| `data/event_outcomes.json` | 14,202 | Event outcome data |
| `data/dumper_outcomes_import.json` | 1,252 | Dumper outcome import data |
| `data/event_effects_scraped.json` | 48,059 | Old scraped effects (replaced by `event_effects.json`) |
| `data/smart_solver_config.json` | 3,198 | Smart solver config |
| `data/skill_config.json` | 56 | Skill config |
| `data/settings_presets.json` | 70 | Settings presets |
| `data/presets/Maru_Fans.json` | 150 | User preset |
| `data/presets/xguri parent.json` | 428 | User preset |
| `scripts/backtest_training_scorer.py` | 450 | Backtest script |
| `_OPTIMIZATION.md` | 272 | Optimization notes |
| `README.md` | 135 | Readme (replaced by different version) |
| Multiple test files | ~1,500+ | Tests for removed features |

### 3.11 Browser Auto-Open Removed

Server no longer auto-opens the browser on startup.

### 3.12 Legacy Classic Engine (`mant.py`)

The entire Classic/Legacy training scorer was deleted from `mant.py` (~800 lines): `_best_command()`, `_score_command()`, all scoring sub-systems, stat target system, and all legacy decision support helpers. `decide()` now always delegates to Trackblazer.

---

## 4. Cherry-Pick Recommendations

### Priority Legend
- **MUST** — Critical improvement, cherry-pick immediately
- **SHOULD** — High value, cherry-pick unless conflicts are severe
- **CONSIDER** — Nice to have, evaluate effort vs. value
- **SKIP** — Not needed or conflicts with master's approach
- **REAPPLY** — Master fork fix that v3-raw reverted; re-apply on top

### 4.1 MUST Cherry-Pick

| Feature | Files | Why |
|---------|-------|-----|
| Late-game item dump system | `items.py` | Solves leftover items more surgically than master's threshold lowering |
| Career log slimming + redaction | `report.py` | 95% log size reduction + security (credential scrubbing) |
| Career resume self-healing | `main.py`, `career_start_recovery.py` | Prevents crashes on stale career resume |
| Deck sanitization | `uma_api/deck_sanitize.py`, `main.py` | Prevents duplicate friend card bugs |
| Canonical race name matching | `trackblazer.py` | Fixes real Triple Crown / epithet matching bugs |
| Guest parent strict mode | `main.py` | Fixes "random umas" guest parent bug |
| Resilient startup | `main.py` | Server survives corrupt data files |
| Aptitude floor fix | `mant_trackblazer.py` | Bug: was always falling back to 6 |
| Milestone slider fix | `mant_trackblazer.py` | Bug: UI wrote different keys than engine read |
| Finale bonus gating (turn >= 73 only) | `mant_trackblazer.py` | Bug: stat cap was shrunken from turn 0 |
| Year-end energy waste prevention | `trackblazer_rules.py`, `items.py` | Don't waste recovery items on year-end turns |
| Manager restart budget | `manager.py` | Prevents infinite restart loops |
| HWID 3-tier fallback | `uma_api/client.py` | Fixes startup failures on newer Windows builds |

### 4.2 SHOULD Cherry-Pick

| Feature | Files | Why |
|---------|-------|-----|
| Rainbow attenuation | `mant_trackblazer.py` | Stops chasing rainbows on capped stats |
| Bond rework (configurable values) | `mant_trackblazer.py` | Enables bond-rushing in junior |
| Planned-skill event preference | `events.py`, `trackblazer_rules.py` | +30 bonus for events hinting planned skills |
| Consecutive race energy management | `items.py` | Smarter pre-race energy use |
| Cupcake type differentiation | `items.py` | Berry Sweet vs Plain for different purposes |
| Group outing stall detector | `runner.py` | Prevents Sirius/Throne career crashes |
| Epithet completion announcements | `runner.py` | Quality-of-life display improvement |
| Per-race running style overrides | `runner.py` | User-configurable per-race style |
| Navbar clock/retry controls | `runner.py` | Runtime retry control |
| Hammer conservation rewrite | `items.py` | Smarter hammer economy than master's dump window |
| Whistle policy (summer + late-game only) | `items.py` | Prevents wasteful whistle firing |
| Rival overwrite support | `races.py` | Manual mode handles rival races |
| Server rejection tracking | `runner.py` | Dashboard health visibility |
| Async snapshot reading | `main.py` | Non-blocking file reads |
| Sirius/Throne group outing system | `mant.py` | Full outing scheduling for group cards |
| Legacy UI improvements | `public/app.js` | Tab bar, per-race styles, export logs, throttle indicator |
| Multi-account health improvements | `main.py` | TCP fallback, self-detection, auto-insert |
| Event system overhaul | `main.py`, `events.py` | Better event matching + full catalog pre-career |
| Retry policy (G1 + CLIMAX default) | `runner.py` | CLIMAX races should be retryable |
| Item pre-race visibility | `runner.py` | Hammers/glow sticks now shown in reasoning panel |

### 4.3 CONSIDER Cherry-Pick

| Feature | Files | Why |
|---------|-------|-----|
| v3 UI (`public-v3/`) | `public-v3/*` | Complete new frontend — large but self-contained; can mount alongside existing UI |
| Card art assets | `data/card_art/*` | Only needed if v3 UI is adopted |
| Higher-res images | `data/images/*` | ~400 files, purely cosmetic upgrade |
| Berry Sweet cupcake skip-recreation | `mant_trackblazer.py` | Saves a recreation turn |
| Finalize single runs | `runner.py` | Plays through URA finale instead of bailing at turn 77; lets new career start without restart |
| Skill intercept (DEV-ONLY) | `main.py` | Development tool, not user-facing |
| Log export endpoint | `main.py` | Nice for debugging, low priority |
| Recreation minimum turn | `mant_trackblazer.py` | Early turns better for bonds |
| Summer all-out energy rescue | `mant.py` | Group deck specific improvement |

### 4.4 SKIP

| Feature | Why |
|---------|-----|
| Remove pacing system | Master's pacing was intentional. Keep it unless you want wire-speed. |
| Remove training scorer | Master doesn't have this as a standalone module either, but verify no regression |
| Remove event outcome KB | Master's fork doesn't use this heavily; low impact either way |
| Remove policy guards | Master's fork doesn't use this heavily |
| Revert `auto_buy_items` priority | Master's fork change is user-facing; keep it |
| Skill purchase retry + verification | `skills.py` — v3-raw has a known bug where skills are not being bought at all. Do not cherry-pick until root cause is identified and fixed. |
| Distance mismatch skill filter | `skills.py` — part of the broken skill system; may be over-filtering valid skills |
| Stop-after-recommended skill gate | `skills.py` — was disabled post-release after "bot buys almost nothing" bug; likely a contributor to the regression |
| Manual skill tiers as first-class mode | `skills.py` — `skill_manual_auto_fallback` defaults OFF, causing bot to buy nothing when manual tiers are stale |
| New skill config keys | `config_store.py` — tied to the broken skill gating logic (`skill_stop_after_recommended`, `skill_manual_auto_fallback`) |
| Skill loading robustness | `skills.py` — low-risk standalone fix, but entangled with the rest of the broken skill rewrite |
| Skill intercept (DEV-ONLY) | `skills.py` — entangled with the broken skill rewrite |

### 4.5 REAPPLY on Top of v3-raw Changes

These are master fork fixes that v3-raw reverted. They must be re-applied after cherry-picking:

| Fix | Files | Why |
|-----|-------|-----|
| Manual aptitude overrides | `main.py`, `public/app.js` | Bugfix: user manual overrides must beat master-data defaults (see CLAUDE.md §main.py) |
| Granular skip reasons in `_skip_buy()` | `items.py` | Log viewer depends on string reasons, not booleans |
| `auto_buy_items` priority in `_item_cap()` | `items.py` | User-facing UI control must be respected |
| Pre-race item logging | `runner.py` | Log viewer depends on `bot_pre_race_use_selected` in career JSON |
| `log_viewer.html` preservation | `log_viewer.html` | Fork-only file, never delete |

---

## 5. File-Level Change Index

### Modified Files (Key Logic)

| File | Lines Changed | Category |
|------|--------------|----------|
| `main.py` | +/- 1,117 | Server, endpoints, startup |
| `career_bot/runner.py` | +/- 882 | Career flow, decisions |
| `career_bot/items.py` | +/- 689 | Item buying/usage |
| `career_bot/skills.py` | +/- 439 | Skill buying (retry, verification, distance filter) |
| `career_bot/scenarios/mant.py` | +/- 1,618 | Main scenario (legacy engine removed, Sirius/Throne outings) |
| `career_bot/scenarios/mant_trackblazer.py` | +/- 243 | Training scorer/decisions |
| `career_bot/events.py` | +/- 211 | Event choice scoring |
| `career_bot/delay.py` | +/- 172 | Timing/pacing (gutted) |
| `career_bot/report.py` | +/- 100 | Career log writing |
| `career_bot/trackblazer.py` | +/- 58 | Race solver |
| `career_bot/trackblazer_rules.py` | +/- 51 | Policy constants |
| `career_bot/character_profiles.py` | +/- 69 | Profile system (simplified) |
| `career_bot/config_store.py` | +/- 21 | Config keys |
| `manager.py` | +/- 56 | Multi-instance supervisor |
| `public/app.js` | +/- 870 | Legacy UI updates |
| `public/index.html` | +/- 54 | Legacy UI markup |
| `uma_api/client.py` | +/- 169 | API client (HWID fallback, rate limit changes) |

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `career_bot/career_start_recovery.py` | 32 | Career resume validation |
| `career_bot/item_helpers.py` | 75 | Item count helpers (extracted from main.py) |
| `uma_api/deck_sanitize.py` | 44 | Deck duplicate handling |
| `data/event_effects.json` | 90,048 | New event effects DB |
| `data/card_names_core.json` | 92 | Per-card versioned names |
| `MIGRATION.md` | 123 | Migration guide |
| `skill_ids.md` | 1,241 | Skill ID reference |
| `public-v3/*` | ~7,000+ | Complete new UI |
| `data/card_art/*.png` | ~90 files | Trainee illustrations |
| Multiple new test files | ~2,000+ | Tests for v3 features |

### Deleted Files

| File | Lines | Impact |
|------|-------|--------|
| `career_bot/training_scorer.py` | 832 | Training scorer removed |
| `career_bot/event_outcomes.py` | 571 | Event KB removed |
| `career_bot/policy_guards.py` | 248 | AI safety rails removed |
| `data/event_outcomes.json` | 14,202 | Event KB data |
| `data/event_effects_scraped.json` | 48,059 | Replaced by `event_effects.json` |
| `data/smart_solver_config.json` | 3,198 | Smart solver config |
| Multiple test files | ~2,500+ | Tests for removed features |

---

## 6. Summary Statistics

| Metric | Count |
|--------|-------|
| Total files changed | 698 |
| Lines added | ~106,218 |
| Lines deleted | ~77,096 |
| New features identified | 33 |
| Improved features identified | 21 |
| Master features removed/reverted | 12 |
| MUST cherry-pick items | 13 |
| SHOULD cherry-pick items | 20 |
| SKIP (broken skill system) | 7 |
| REAPPLY fork fixes | 5 |

---

## Known Issues on v3-raw

### CRITICAL: Bot not buying skills

v3-raw is observed to not purchase skills during careers, unlike master. Likely causes (in order of suspicion):

1. **`skill_stop_after_recommended`** — defaults OFF but was bugged and disabled post-release ("disabled after a bug caused the bot to buy almost nothing"). If re-enabled or misconfigured, it halts all candidate generation after the recommended list is exhausted.
2. **`skill_manual_auto_fallback` defaults OFF** — if manual skill tiers are populated (even with stale IDs), the bot buys ONLY those skills and does NOT fall back to auto. On master, manual tiers were gated behind a separate toggle and auto always ran.
3. **`_skill_distance_mismatch()` filter** — new hard filter may be too aggressive, dropping valid skills as "off-distance" for trainees with ambiguous distance profiles.
4. **`_acquired_skill_ids` false positives** — the career-persistent set may over-accumulate IDs from state snapshots, falsely marking skills as already owned.
5. **`_confirm_purchases()` retry exhaustion** — the 3-attempt verification loop may reject valid purchases if the post-buy state refresh is slow or inconsistent.

**Recommendation for `master-v3-merge`:** When cherry-picking the skill purchase retry/verification (§1.21), carefully test with a live career. The retry loop and `_acquired_skill_ids` tracking are valuable bug fixes, but the gating logic (`skill_stop_after_recommended`, `skill_manual_auto_fallback`, distance mismatch) must be verified against actual skill buying behavior before merging.

### API Communication: 205/208 errors

- v3-raw had API communication issues (205/208 errors on `single_mode_free/start`). These are server-side/networking issues, not code bugs — do not block cherry-picking on this.

---

## Notes

- The v3-raw API 205/208 errors are networking issues, not code bugs.
- The `public-v3/` UI is self-contained and can be mounted alongside the existing UI without conflicts if desired.
- The biggest architectural shift is the removal of the legacy/Classic training scorer (~800 lines from `mant.py` + 832 lines `training_scorer.py`). Trackblazer is now the sole engine. This simplification is good but means all training quality depends on `mant_trackblazer.py`.
- The item management philosophy shifted from "lower thresholds globally" (master fork) to "keep standard thresholds + structured late-game dump windows" (v3-raw). The v3-raw approach is more surgical and avoids mis-spending items early.
