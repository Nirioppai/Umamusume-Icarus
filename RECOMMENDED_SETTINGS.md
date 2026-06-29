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

---

## Settings History

Newest first. Each entry documents what changed and why.

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
