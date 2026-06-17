# Skill Profile Card ID Compatibility

## Purpose

This compatibility fix prevents generated trainee profiles from crashing the skill profile matcher when card IDs appear as scalar values rather than arrays.

## Problem

Some generated profiles used:

```json
{
  "card_id": 100101
}
```

instead of:

```json
{
  "card_ids": [100101]
}
```

The matcher attempted to iterate the integer and raised:

```text
TypeError: 'int' object is not iterable
```

## How it works

`career_bot/skills.py` now accepts:

- `card_ids` as a list, tuple, or set
- `card_ids` as a string
- `card_id` as an integer or string scalar
- missing card ID values

The matcher normalizes these forms before comparison.

## Dependencies and interactions

This fix interacts with generated trainee skill profiles, dynamic skill profiles, and skill recommendation matching. It is defensive compatibility logic and does not alter skill scoring priorities by itself.

## Verification

Run `tests/test_skill_profile_scalar_card_id_v49.py` or load a generated profile containing scalar `card_id` and confirm skill recommendations do not crash.
