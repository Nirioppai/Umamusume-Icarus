# AI learning — Live Policy Assistance, shadow mode, and the dataset

This is the user guide for the AI Learning panel. The system learns
from your past careers and can gently influence future race
selections — but only when its predictions have proven accurate
enough.

## Two systems, one panel

The AI Learning panel surfaces two distinct subsystems people often
confuse:

| System | Where | Affects | Default |
|---|---|---|---|
| **Live Policy Assistance (LPA)** | AI Learning tab toggle | **Race** selection (solver-time) | OFF |
| **Training Scorer Mode** | Character Profile tab dropdown | **Training** selection (per-turn) | hint |

They never conflict. LPA biases which races the solver plans;
Training Scorer Mode biases which training the strategy picks each
turn.

## Live Policy Assistance: what it does

LPA uses learned data from past careers' race outcomes. When enabled,
it applies small score adjustments to race candidates in the Smart
Race Solver based on which races have historically failed for similar
trainees. It only modifies SCORING — it never overrides safety gates,
race availability, or forced races.

## When the dashboard says "Recommended: ENABLE"

The recommendation banner has a precision gate (v6.7.8) on top of the
older data-sufficiency checks:

| Gate | Default | Why |
|---|---|---|
| Turn records ≥ 250 | yes | Need volume |
| Race-result coverage ≥ 85% | yes | Need clean labels |
| Race rows ≥ 50 | yes | Need diversity |
| Learned adjustments ≥ 1 | yes | Model has something to apply |
| **Shadow precision ≥ 60%** | yes (v6.7.8) | Model's predictions actually right |
| Min shadow evaluations ≥ 100 | yes | Precision is statistically meaningful |

The precision gate is the most important — without it, a model that's
confidently wrong (high learned-adjustment count, low actual accuracy)
would get green-lit.

Both thresholds are configurable in the auto-config:

- `min_shadow_precision` — default 0.60
- `min_shadow_evaluations` — default 100

## Shadow mode: how accuracy is measured

Shadow mode runs the model in evaluate-only mode against historical
races. For each race where the model predicted "this might fail"
(negative adjustment), shadow checks the actual outcome:

- **Useful warning** — model said "risky", race actually didn't get
  rank 1
- **False alarm** — model said "risky", race actually got rank 1

**Precision = useful / (useful + false_alarms)**.

A precision of 60%+ means the model's risk warnings are reliable
enough that suppressing those races is net-positive for your race
count. Below 60%, enabling LPA would hurt race count more than help.

## Why precision is hard to climb past 50% early on

The dataset learns from your trainees. If you've only run Oguri Cap
careers, the model has only seen ONE trainee's race-outcome
distribution. That's not enough diversity for the model to generalize.

To improve precision:

1. **Run more careers** — at least 50 across multiple trainees
2. **Vary trainees** — Special Week, Daiwa Scarlet, Tokai Teio,
   Sakura Bakushin O all have shipped profiles and different
   aptitudes
3. **Vary support decks** — the model uses support-card density as a
   feature
4. **Check shadow precision periodically** — once it crosses 60%
   with ≥ 100 evaluations, the dashboard will flip the
   recommendation to ENABLE on its own

## The dataset and what it captures

The AI dataset is built from your career logs in
`uma_runtime/<profile>/bot_logs/`. Each log captures:

- Per-turn state snapshots (chara_info, home_info, command_info)
- Action chosen + reason
- Race outcomes (rank, fans gained, performance hints)
- Item usage and shop interactions
- Final career snapshot

Three derived tables are computed:

- **Race outcome table** — per-race historical rank distribution
  keyed by program_id + trainee context
- **Item effectiveness table** — which items have produced positive
  outcomes
- **Event outcome table** — choice-driven event outcomes

These tables drive the live policy adjustments when LPA is enabled.

## Rebuilding the model

Run `python -c "import career_bot.ai_dataset as d; d.rebuild_from_career_logs('./')"`
to regenerate from current logs. The dashboard's "Train" button does
the same. Useful after a big batch of new careers.

## Style adaptation

A parallel system tracks per-trainee running-style outcomes and
recommends style overrides when one style consistently outperforms
the trainee's default. Configurable from the AI Learning panel.

- Auto-apply unlocks at 10+ style-change outcomes
- Reverts on poor downstream performance
- Logged to `style_adaptation` block in the AI status payload
