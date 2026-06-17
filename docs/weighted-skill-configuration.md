# Weighted Skill Configuration

## Purpose

Configure Skills is now the single UI for automated skill point spending. It uses the weighted skill purchase system and no longer shares storage with Settings Presets.

## Main Controls

- **Enable Skill Point Check**: enables automatic skill purchases.
- **Skill Point Threshold**: the number of skill points to accumulate before purchasing skills. This does not stop the bot.
- **Enable Skill Point Check Plan**: enables the configured weighted plan when the threshold is reached.
- **Purchase All Negative Skills**: allows negative skills to be considered for purchase.
- **Skip Green Skills**: filters green stat-trigger skills.
- **Skip Red Skills**: filters red debuff skills.
- **Skip Unique Skills**: filters inherited unique legacy skills.
- **Automated Skill Point Spending Strategy**: chooses either Best Skills First or Optimize Rank.
- **Planned Skills / Blacklist**: click skills in the library to pin or block them.

## Read-Only Context

Configure Skills shows these as read-only summaries:

- Running Style: sourced from Racing Settings.
- Track Distance: sourced from Training/trainee context.
- Track Surface: sourced from the weighted skill strategy or defaults.

This prevents duplicate controls from fighting over race strategy or distance behavior.

## Storage

Settings are saved in:

```text
data/skill_config.json
```

They are not saved inside Settings Presets.

## Runtime Behavior

`SkillBuyer.buy()` uses `learn_skill_threshold` as a purchase gate. If the trainee has fewer or equal skill points than the threshold, no skills are bought and the runner continues.

Skill filters are applied to candidates before buying:

- green skip
- red skip
- unique skip
- negative skill inclusion/exclusion

`skill_spending_strategy = optimize_rank` sorts by score-per-cost efficiency. `best_skills_first` keeps the weighted score order.

## Verification

Run:

```bash
python -m unittest tests.test_sweepymodv59_config_split -v
```

Open Configure Skills, change threshold/filter values, refresh, and confirm they persist in `data/skill_config.json`.
