# Trackblazer Decision Safety

## Purpose

Trackblazer Decision Safety reduces bad automation decisions during race-heavy runs by adding irregular-training gates, race-chain awareness, low-energy safety, and stricter Reset Whistle behavior.

## Irregular Training

Irregular Training lets the bot skip a planned voluntary race when a high-value training turn appears. It:

- starts from Classic year behavior, not early Junior turns
- skips summer camp and Finale turns
- requires a minimum main-stat gain
- permits higher-failure hijacks only if Good-Luck Charm is owned and the gain is worth protecting
- records trace fields for score, failure rate, main gain, planned race, and Charm availability

## Consecutive race safety

The runner injects action history into strategy state so Trackblazer can detect real recent race streaks. After unsafe race chains, the strategy prefers a strong training turn, then recovery when HP is low or critical. Low-grade voluntary races are treated as unsafe once the streak is already long.

## Reset Whistle rescue

Reset Whistle is treated as a dead-turn rescue item. It is blocked when:

- low HP is the real problem
- low motivation is the real problem
- the bot is performing irregular-training item setup
- Whistle already succeeded this turn

After item use, runner logic re-evaluates the command so stale pre-Whistle training choices are avoided.

## Dependencies and interactions

Implemented in `career_bot/scenarios/mant.py`, `career_bot/items.py`, and `career_bot/runner.py`. It depends on item inventory, action history, training command analysis, and Trackblazer configuration.

## Verification

Run `tests/test_trackblazer_p1_decisions.py`. During a career, inspect decision traces after race streaks and confirm voluntary low-grade races are avoided when unsafe.
