# Trackblazer Event Scoring

## Purpose

Trackblazer Event Scoring improves automatic event-choice fallback selection by evaluating reward details instead of relying only on fixed overrides or shallow defaults.

## How it works

`career_bot.events.EventManager` scores event options using parsed reward details, including:

- stat gains and losses
- skill points
- vitality/energy
- motivation/mood
- bond/friendship
- skill hints
- positive and negative statuses
- event-chain unlock flags
- event-chain ending penalties
- random reward penalties or bonuses

## Configuration

Event stat priority can be configured separately from training priority:

```json
{
  "event_choice_stat_priority": ["stamina", "power", "speed", "guts", "wit"]
}
```

Energy-priority mode can make low-energy recovery choices much stronger:

```json
{
  "prioritize_event_energy": true,
  "event_energy_priority_multiplier": 100
}
```

## Tracing

Event traces include:

- stat priority used
- whether energy-priority mode was active
- per-choice scores
- per-choice scoring reasons

## Dependencies and interactions

Implemented in `career_bot/events.py`, with serialization support in `career_bot/presets.py` and constants in `career_bot/trackblazer_rules.py`. It interacts with Training Settings through Event Choice Prioritization.

## Verification

Run `tests/test_trackblazer_p3_events.py`. Trigger an event with multiple options and inspect the event trace to confirm scores and reasons are reported.
