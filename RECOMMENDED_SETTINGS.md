# RECOMMENDED_SETTINGS.md — Optimal Bot Configuration

Current best-known settings for the Icarus Trackblazer bot, maintained by
comparing AI summary feedback across career runs. When a run produces better
results (higher total stats, better win rate, better item efficiency, better
Climax outcomes), its settings become the new recommendation.

Referenced by [CLAUDE.md](CLAUDE.md) (auto-update rule).

---

## How This File Works

1. The log viewer's **AI Summary Export** includes the full settings snapshot
   from the career run.
2. When that summary is fed to an AI agent, the agent compares the run's
   performance against the current recommendation here.
3. If the run outperforms (evidence required), the agent updates the
   **Current Recommended Settings** section with the new values and adds
   a dated entry to **Settings History** explaining what changed and why.

---

## Current Recommended Settings

**Baseline date:** 2026-06-29
**Source:** v3.2.2 defaults + nirio fork tuning (integration rationale, not A/B tested)
**Evidence:** Strong baseline run: 4030 total stats, 92.1% win rate, Climax mood Great, 54 coins remaining, 3 MCH at T73

### Training Settings

| Setting | Value | Rationale |
|---|---|---|
| Stat Focus Mode | balanced | Even-completion curve; capped mode over-concentrates |
| Training Blacklist | (none) | No stats excluded by default |
| Prioritization | Speed > Power > Wit > Stamina > Guts | Standard Trackblazer priority |

### Skill Settings

| Setting | Value | Rationale |
|---|---|---|
| Skill Point Threshold | 888 | Default; below this SP, no buying |
| Skill Optimization Target | career | Fans-first single-mode; TT/CM for finished umas |
| Skill Condition Gating | penalize | Dampen dead skills to 15% eval/SP instead of hard-drop |
| Pre-Finals Skill Dump | ON | Spend accumulated SP before Climax at turn 73 |

### Racing Settings

| Setting | Value | Rationale |
|---|---|---|
| Max Races in Row | 5 | Planning cap for consecutive races |
| Live Re-Planning | ON | Re-solve schedule when races are lost/unavailable |
| Re-Plan Only on Race Events | ON | Prevents per-turn churn that piles up streaks |
| Distance Preference Mode | balanced | Moderate adherence to trainee distances |
| Include OP/Pre-OP | OFF | Lower-grade races only for weak characters |

### Scenario Overrides

| Setting | Value | Rationale |
|---|---|---|
| Energy Threshold | 40 | Use energy items when vital drops below this |
| Force-Train Energy Floor | 20 | Minimum vital for forced training |
| Cupcake Reserve | 1 | Keep 1 cupcake for kale-juice synergy |
| Master Hammer Finale Reserve | 3 | Upstream slider; dynamic reserve reduces this |
| Artisan Hammer Min Stock G3 | 0 | No gate on G3 Artisan spending |
| Artisan Hammer Min Stock G2 | 0 | No gate on G2 Artisan spending |
| Glow Stick Final Reserve | 1 | Keep 1 glow stick for finale |
| Glow Stick Min Fans | 20000 | Minimum fans for glow stick usage |
| Save Items Late Game | OFF | Dump items aggressively after turn 64 |
| Shop Check Frequency | 1 | Check shop every opportunity |

### (NIRIO) Fork Tuning

| Setting | Value | Rationale |
|---|---|---|
| Skill Force Turn | 60 | Force skill buying 13 turns earlier than default 73 |
| Skill SP Floor | 500 | Minimum SP for forced buying |
| Skill Hoard Threshold | 1000 | Buy immediately above this (vs upstream 1500) |
| Mood Repair Turn | 50 | Start aggressive cupcake use for mood recovery |
| Mood Floor | 2 | Trigger mood repair when motivation <= 2 |
| Mood Critical Turn | 68 | Hard-block race chains when mood low after this |
| Chain Mood Floor | 2 | Block chains when motivation <= this |
| Charm Dump Turn | 60 | Lower Good-Luck Charm thresholds after this |
| Charm Dump Min Gain | 8 | Minimum stat gain for charm in dump window |
| Charm Dump Failure Rate | 10 | Min failure rate for charm in dump window |
| Whistle Dump Turn | 60 | Allow whistle usage earlier than default 65 |
| MCH Climax Reserve | 3 | Master hammers protected for Climax (dynamic) |
| Final MCH Required **(new)** | 2 | MCH to protect for later Climax races; T74 gets MCH only if 3+ owned |
| Final Artisan Reserve **(new)** | 1 | Artisan fallback kept for later Climax races when MCH is tight |

---

## Settings History

Newest first. Each entry documents what changed and why.

### 2026-06-30 — Long Pace V3 Fix, nirio_chain_mood_floor=4, MCH reserve-2

**Source:** Long Pace V3 Fix preset, Make a New Track scenario, 77/77 turns
**Classification:** MIXED — do not update Current Recommended Settings

Settings tested:
- nirio_chain_mood_floor: 4
- nirio_charm_dump_failure_rate: 10
- nirio_charm_dump_min_gain: 8
- nirio_charm_dump_turn: 60
- nirio_final_artisan_reserve: 1
- nirio_final_mch_required: 2
- nirio_mch_reserve: 2
- nirio_mood_critical_turn: 65
- nirio_mood_floor: 4
- nirio_mood_repair_turn: 50
- nirio_skill_force_turn: 60
- nirio_skill_hoard_threshold: 1600
- nirio_skill_sp_floor: 1500
- nirio_whistle_dump_turn: 60

Result:
- Final stats: 3709 (Speed 973, Stamina 816, Power 1009, Guts 480, Wit 431)
- Win rate: 100% (29/29 races), G1 14/14
- Climax mood: Great (T76)
- SP remaining: 105 (CRITICAL — 0 skills purchased, all SP wasted)
- Final coins: 7
- Real leftovers per final_inventory: MCH ×2, Ankle Weights (Power) ×3, Vita (65) ×1 (7 total)
- Unused stat items (corrected via final_inventory): 0 (ledger drift from instant-use items resolved)
- Note: previous log viewer per-item table showed ~165 stats lost from scrolls/manuals; this was
  ledger drift — those items were consumed on the same turn they were bought (instant-use).
  After the log viewer fix, final_inventory correctly shows 0 leftover stat items.

Trade-offs vs baseline (4030 stats, 92.1% win rate):
- Stats (3709) significantly below baseline (4030).
- Win rate (100%) better than baseline (92.1%).
- G1 win rate (100%) better than baseline (89%).
- Climax mood Great — matches baseline.
- SP: CRITICAL — skill buying completely failed. nirio_skill_force_turn=60 with
  nirio_skill_sp_floor=1500 did not trigger because SP threshold wasn't reached early enough.
- Power Ankle Weights ×3 unused — bought too early (T46-T47) before conservation lifted.
- Vita (65) ×1 unused — bought at T74 finale but no turns remaining to use it.

Decision:
Do not promote. Stats significantly below baseline. Skill buying failure is a critical regression —
the combination of nirio_skill_hoard_threshold=1600 and nirio_skill_sp_floor=1500 creates a
catch-22: the bot accumulates SP above the hoard threshold but the force turn hasn't triggered, and
by force turn 60 the threshold is still too high for the bot to act. Lower nirio_skill_sp_floor to
500 (recommended default) or lower nirio_skill_hoard_threshold back to 1000.
Power Ankle Weights leftover: bot bought 4 but only used 1. Ankle weight conservation gates
(trackblazer_anklet_max_stock=3) may need lowering to 2 for this preset.

---

### 2026-06-30 — Long Pace V3 Fix, reserve-2 hammer policy test

**Source:** Long Pace V3 Fix preset, Make a New Track scenario
**Classification:** PROVISIONAL — do not update Current Recommended Settings (leftover accounting suspect)

Settings tested:
- nirio_mch_reserve: 2
- nirio_final_mch_required: 2
- nirio_final_artisan_reserve: 1
- nirio_chain_mood_floor: 4
- nirio_mood_floor: 4
- nirio_mood_critical_turn: 65

Result:
- Final stats: 3815
- Win rate: 93.5% (31/33 races, 14/14 G1, 2/2 Climax)
- Climax mood: Good
- SP remaining: 23
- Final coins: 136
- Reported leftovers: 29 (low-confidence — ledger/inventory mismatch confirmed)
- Real leftovers per final_inventory: Power Anklets ×4, Reset Whistles ×2, MCH ×2, Artisan ×1, Glow Sticks ×1

Trade-offs vs baseline (4030 stats, 92.1% win rate):
- Stats (3815) below baseline (4030).
- Win rate (93.5%) slightly better than baseline (92.1%).
- G1 win rate (100%) better than baseline (89%).
- Climax mood Good vs Great — marginally worse.
- T73 MCH: 2 available (intentional per new reserve-2 + final_mch_required=2 policy).

Decision:
Do not promote. Stats below baseline despite better race quality. Per-item leftover accounting is bugged
(ledger reported leftover manuals/carrots/scrolls not present in final_inventory or confirmed in-game at T77).
MCH reserve 2 with final_mch_required=2 + final_artisan_reserve=1 appears viable. Main issues: Power Anklets
and Reset Whistles still not dumping. Fix log viewer accounting before next comparison.

---

### 2026-06-30 — Long Pace V3 Fix mixed result

**Source:** Long Pace V3 Fix preset, Make a New Track scenario, 78/78 finished
**Classification:** MIXED — do not update Current Recommended Settings

Tested settings:
- nirio_chain_mood_floor: 3
- nirio_mch_reserve: 2
- nirio_mood_floor: 4
- nirio_mood_critical_turn: 68
- nirio_mood_repair_turn: 50
- nirio_skill_hoard_threshold: 1600
- nirio_skill_sp_floor: 1500
- nirio_skill_force_turn: 60
- nirio_whistle_dump_turn: 60
- nirio_charm_dump_turn: 60
- nirio_charm_dump_min_gain: 8
- nirio_charm_dump_failure_rate: 10

Result:
- Final stats improved to 4180 (best so far, up from 4030 baseline).
- SP cash-out improved dramatically: 44 SP remaining (down from 2429).
- Item leftovers improved: 26 items left (down from 37).
- Final coins acceptable: 67.
- Full run completed: 78/78 finished (baseline stopped at 76/76).

Trade-offs:
- Win rate dropped to 81.1% (baseline 92.1%).
- G1 win rate dropped to 72% (baseline 89%).
- Climax mood was Awful (baseline Great).
- T73 Master Hammer reserve was only 2, below the intended 3-MCH plan for T74/T76/T78.
- ~365 unused permanent stat value (slightly better than ~420 but still high).
- Power anklets ×2 still unused.

Decision:
Do not promote. The SP cash-out and skill spending behavior is promising and
should be preserved, but mood protection and MCH reserve need correction.
Next candidate should restore nirio_mch_reserve=3, add final-window mood
protection after T70, and continue reducing permanent stat item leftovers.

---

### 2026-06-29 — Initial baseline (v3.2.2 + nirio integration)

**Source:** v3.2.2 defaults with nirio fork tuning applied
**Evidence:** Strong baseline run (4030 total stats, 92.1% win rate, Climax Great)
**Changes:** Initial population from integration rationale. Not A/B tested —
these are the settings that produced the known-good baseline run. Future runs
that outperform should update the recommended values above.

**Nirio tuning rationale:**
- Skill Force Turn 60 (was 73): bot hoarded 2000+ SP until pre-finals dump
- Hoard Threshold 1000 (was 1500): more aggressive spending trigger
- Mood Floor 2 / Repair Turn 50: prevented Climax mood collapse (Bad → Great)
- Charm Dump Turn 60: reduced Good-Luck Charm leftovers from 3 to 0-1
- Whistle Dump Turn 60: reduced Reset Whistle leftovers from 2 to 0-1
- MCH Reserve 3 (dynamic): protects exactly N Masters for N remaining Climax races

**Superseded nirio knobs (v3.2.2 upstream is better):**
- Mega dump turn/multiplier: upstream drops score floor entirely in dump mode
- Anklet dump turn/multiplier: upstream drops score floor in dump mode
- Cashout conservation: upstream's save_items_lategame toggle is correct
