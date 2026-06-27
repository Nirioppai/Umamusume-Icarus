# Eden Icarus — Settings Optimization Guide (Max Stats Build)

> Generated 2026-06-25 from source code analysis.
> Goal: **maximum stats** — willing to sacrifice race count and fans.
> Current state: 2 careers, 156 turns, Ollama LLM connected (`gemma4:12b`).

---

## Where to find each setting

Settings are spread across several UI panels. This section maps each panel
so you know where to go before touching anything.

### Top bar — Speed buttons

Right at the top of the dashboard, four buttons in a row:
**Safe | Fast | Faster | Ludicrous**

| Setting | Where |
|---------|-------|
| Speed level | Click one of the four speed buttons at the top of the page |

### TRAINING SETTINGS panel

Open via the **TRAINING SETTINGS** button in the main dashboard section.
The "Goal-aware lookahead" checkbox is in the **top bar** of this panel
(next to the DONE button).

| Setting | Section inside panel |
|---------|---------------------|
| `training_stat_priority` | Priorities > Prioritization (drag to reorder) |
| `event_choice_stat_priority` | Priorities > Event Choice Prioritization |
| `summer_stat_priority` | Priorities > Summer Training Prioritization |
| `stat_focus_mode` | Behavior > Stat Focus dropdown |
| `maximum_failure_chance` | Behavior > Set Maximum Failure Chance slider |
| `enable_risky_training` | Behavior > Enable Riskier Training toggle |
| `enable_rainbow_training_bonus` | Scoring > Rainbow Training Bonus toggle |
| `enable_near_rainbow_bonus` | Scoring > Near-Max Friendship Boost toggle |
| `disable_stat_targets` | Distance > Disable Stat Targets toggle |
| Stat Targets grid | Distance > Stat Targets by Distance table |
| `goal_lookahead` | **Panel top bar** > "Goal-aware lookahead" checkbox |

### RACING SETTINGS panel

Open via the **RACING SETTINGS** button.

| Setting | Section inside panel |
|---------|---------------------|
| `enable_outcome_risk` | Outcome Risk > Enable Outcome-Risk Avoidance |
| `outcome_risk_weight` | Outcome Risk > Outcome-Risk Weight slider |
| `ignore_low_energy_racing_block` | Race Behavior > Ignore Low Energy Racing Block |
| `ignore_consecutive_race_warning` | Race Behavior > Ignore Consecutive Race Warning |

### SMART RACE SOLVER SETTINGS modal

Open via the **SMART RACE SOLVER SETTINGS** button (in the Smart Race Planner
area of the dashboard).

| Setting | Section inside modal |
|---------|---------------------|
| `min_aptitude_floor` | Aptitude grade buttons (S/A/B/C/D/E/F/G row) |
| `include_op` | "Include OP / Pre-OP races" toggle |
| `distance_preference_mode` | Distance Preference Mode buttons (Strict/Balanced/Loose) |
| `allowSummerRacing` | (toggle if visible, else already off by default) |
| **Scoring Weights** subsection: | |
| `fanWeight` | Fan Weight |
| `consecutiveRacePenalty` | Consecutive Race Penalty |
| `raceBonusPct` | Race Bonus % |
| `raceCostPct` | Race Cost % |
| `max_races_in_row` | Max Streak |
| `epithetValue` | Epithet Value Weight |
| `raceValue` | Race Value Weight |
| Optimization preset | Optimization Weight Preset > "Stat Epithets" or "Fans + Epithets" |

> **Note:** `targetOptionalRaceCount`, `lateSeniorRacePressure`, and
> `lateSeniorFanPressure` are backend-only solver weights. They are **not
> exposed in the UI**. To change them, edit the file
> `data/trackblazer_solver_defaults.json` (create it if it doesn't exist) with
> the keys and values listed below.

### AI / MISC section

Scroll down to the **AI / MISC** collapsible section at the bottom of the
dashboard.

| Setting | Where in AI / MISC |
|---------|-------------------|
| Live Policy Assistance | Toggle near the top of the AI section |
| Auto-train after careers | Auto-training config area |
| Shadow mode | AI auto-training config |
| Local LLM mode | Local LLM Advisor card > Mode dropdown |
| Style Adaptation mode | Racing Style Adaptation card > Mode dropdown |

---

## Recommended Settings

### 1. Race / Training Balance (Smart Race Solver Settings modal)

| Setting | Default | Recommended | Reason |
|---------|---------|-------------|--------|
| Max Streak | 5 | **3** | Fewer consecutive races = more training turns. |
| Include OP | off | **off** | OP races return +5 stat / +15 SP — terrible vs a training turn. |
| Aptitude Floor | C | **A** | Only enter A+ aptitude races. Fewer races, better win rate. |
| Distance Preference | Balanced | **Strict** | Sticks to best aptitude distance; avoids off-distance waste. |
| Optimization Preset | — | **Stat Epithets** | Biases solver toward stat return over fans. |
| Fan Weight | 0.001 | **0.0005** | Halved — you're sacrificing fans for stats. |
| Consecutive Race Penalty | 3.0 | **6.0–8.0** | Discourages back-to-back races, preserves energy for training. |
| Race Cost % | 100 | **130–150** | Increases solver's perceived cost of each race. |
| Race Bonus % | 50 | **30** | Reduces reward for racing stat bonuses; biases toward training. |

### 2. Backend-only solver weights (`data/trackblazer_solver_defaults.json`)

Create this file if it doesn't exist. These keys are read by the solver but
have no UI knob:

```json
{
  "targetOptionalRaceCount": 26,
  "lateSeniorRacePressure": 6.0,
  "lateSeniorFanPressure": 0.00012,
  "outcomeRiskWeight": 1.5
}
```

| Setting | Default | Recommended | Reason |
|---------|---------|-------------|--------|
| `targetOptionalRaceCount` | 36 | **26** | Solver targets this many optional races. Lower = more training. |
| `lateSeniorRacePressure` | 12.0 | **6.0** | Reduces panic racing in late Senior year. |
| `lateSeniorFanPressure` | 0.00025 | **0.00012** | Less fan-chasing pressure in final turns. |
| `outcomeRiskWeight` | 1.0 | **1.5** | Harder penalty on historically lost races. |

### 3. Training Settings (Training Settings panel)

| Setting | Default | Recommended | Reason |
|---------|---------|-------------|--------|
| Stat Focus | Balanced | **Capped** | Concentrates on priority stats to 1200 cap. **Biggest single lever.** |
| Goal-aware lookahead | off | **on** | Boosts lagging stats, trims ahead-of-pace. Free accuracy gain. |
| Rainbow Training Bonus | on | **on** | Already correct — keep the rainbow multiplier active. |
| Max Failure Chance | 20 | **20** | Default is solid. Higher risks stat loss. |
| Riskier Training | off | **off** | Not worth the variance for average stats. |

**Stat priority order by distance** (drag to reorder in Priorities section):

| Distance | Priority Order (top to bottom) |
|----------|-------------------------------|
| Sprint | Speed > Power > Wit > Stamina > Guts |
| Mile | Speed > Power > Wit > Stamina > Guts |
| Medium | Speed > Power > Stamina > Wit > Guts |
| Long | Stamina > Speed > Power > Wit > Guts |

Set the same order for Training, Event Choice, and Summer priorities.

**Stat Targets by Distance** (in the Distance section grid):

| Distance | Speed | Stamina | Power | Guts | Wit |
|----------|-------|---------|-------|------|-----|
| Sprint | 1200 | 600 | 1200 | 600 | 1200 |
| Mile | 1200 | 600 | 1200 | 600 | 1200 |
| Medium | 1200 | 800 | 1200 | 600 | 1200 |
| Long | 1200 | 1000 | 1200 | 500 | 1000 |

### 4. Racing Settings (Racing Settings panel)

| Setting | Default | Recommended | Reason |
|---------|---------|-------------|--------|
| Outcome-Risk Avoidance | on | **on** | Penalizes historically lost races. Keep. |
| Outcome-Risk Weight | 1.0 | **1.5** | (Also settable in solver defaults JSON above.) |
| Ignore Low Energy Block | off | **off** | Safety gate — don't override. |
| Ignore Consecutive Warning | off | **off** | Let the streak limiter work. |

### 5. AI / LLM Settings (AI / MISC section)

| Setting | Current | Recommended | Reason |
|---------|---------|-------------|--------|
| Live Policy Assistance | OFF | **OFF (for now)** | Only 2 careers. Need 5+ starts per race program. |
| Auto-train after careers | 1 | **1** | Already correct. Rebuilds model every career. |
| Shadow mode | on | **on** | Backtests AI model against results. Keep. |
| Local LLM mode | Offline | **Shadow Advisor** | Auto-reviews every turn, builds richer advice log. |
| Style Adaptation | Shadow | **Shadow** | Auto Apply locked until 100+ experiences. Correct for now. |

### 6. Speed (top bar)

| Setting | Default | Recommended | Reason |
|---------|---------|-------------|--------|
| Speed level | Safe | **Fast** | Disables inter-turn delay, keeps 0.14s API floor. ~3x faster careers. |

Available levels:

| Level | Turn Delay | API Scale | API Floor |
|-------|-----------|-----------|-----------|
| Safe | 2.5–5.0s | 1.0x | 0.14s |
| Fast | disabled | 0.4x | 0.14s |
| Faster | disabled | 0.15x | 0.05s |
| Ludicrous | disabled | 0x | 0s |

Fast is the sweet spot. Faster/Ludicrous risk rate limiting.

---

## What to Do Right Now (ordered by impact)

1. **Set Stat Focus to Capped** — Training Settings > Behavior > Stat Focus dropdown.
   This is the single biggest lever. It concentrates training on your priority
   stats instead of spreading evenly across all five.

2. **Enable Goal-aware lookahead** — Training Settings panel top bar checkbox.
   Free accuracy improvement that dynamically adjusts stat priorities by pace.

3. **Lower Max Streak to 3** — Smart Race Solver Settings > Scoring Weights > Max Streak.
   Every race skipped is a training turn gained.

4. **Set Distance Preference to Strict** — Smart Race Solver Settings > Distance
   Preference Mode buttons.

5. **Raise Aptitude Floor to A** — Smart Race Solver Settings > grade button row.

6. **Raise Consecutive Race Penalty to 6–8** and **Race Cost % to 130–150** —
   Smart Race Solver Settings > Scoring Weights section.

7. **Select Stat Epithets optimization preset** — Smart Race Solver Settings >
   Optimization Weight Preset section.

8. **Create `data/trackblazer_solver_defaults.json`** with the JSON above to
   lower the target race count and late-senior pressure.

9. **Set speed to Fast** — top bar speed buttons. Faster careers = more data sooner.

10. **Switch Local LLM mode to Shadow Advisor** — AI / MISC > Local LLM Advisor >
    Mode dropdown.

11. **Import bundled event outcomes** if not done — AI / MISC > Event Outcome
    Knowledge Base > IMPORT BUNDLED OUTCOMES button.

---

## What to Do After 10+ Careers

- **Enable Live Policy Assistance** — the policy guard requires `min_samples_per_cell`
  = 5 starts per race program. With 2 careers you're far below that. The guard caps
  adjustments at 25% of heuristic score and 50 raw points, so it's safe to enable
  once you have data — but it's pure noise until then.

- **Watch Shadow Mode precision** — when it shows >70% precision across 20+ evaluated
  hints, Live Policy is trustworthy.

- **Enable Style Adaptation "recommend" mode** — after enough races to compute
  per-style win rates. Auto Apply needs 100+ experiences and 20+ observed switches
  with <20% bad switch rate.

- **Run Backtest periodically** — when "captured historical failed races" exceeds 60%,
  the learned model is becoming useful.

- **Consider raising `liveAiConfidenceThreshold`** from 0.65 to 0.75 — only apply AI
  hints when the model is very confident.

---

## Settings to Leave Alone

| Setting | Default | Why |
|---------|---------|-----|
| Rest Threshold | 30 (Trackblazer) | Already aggressive. Lower risks failed trainings. |
| Max Failure Chance | 20 | Standard gate. Higher introduces stat-loss variance. |
| Enable Riskier Training | off | Not worth the average-case stat loss. |
| Summer Block Penalty | 5.0 | Already prevents summer racing. |
| Forced Epithet Value | 500 | Only for specific epithet targeting. |
| Auto-train interval | 1 career | Right cadence. |
| Compensate Failure | on | Scorer already factors in failure rate. |
| Skill Threshold | 888 | Skill purchasing — doesn't affect training stats. |
| Include OP | off | Terrible stat return per turn. |
| Allow Summer Racing | off | Summer camp training is too valuable. |
