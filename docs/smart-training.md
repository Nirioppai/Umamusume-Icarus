# Smart Training and Rainbow Scoring

## Purpose

Smart Training improves training-command selection by valuing friendship/rainbow opportunities, avoiding wasteful full-HP Wit choices, and showing clearer decision reasons.

## How it works

Training selection weighs command gains, partner presence, friendship/rainbow signals, and preset tuning fields. When rainbow training is detected, the command reason includes visible text such as:

```text
rainbow x2
```

Wit training is no longer chosen at full HP by default just for recovery value, because the recovery would be wasted when HP is already full.

## Configuration

Supported tuning fields include:

```json
{
  "rainbow_training_bonus": true,
  "rainbow_training_stack_bonus": 1.0,
  "rainbow_partner_value": 1.0,
  "allow_full_hp_wit_rainbow": false
}
```

Later Trackblazer settings extend this with `mant_config.enable_rainbow_training_bonus`, `mant_config.enable_near_rainbow_bonus`, and `mant_config.enable_training_level_weighting`.

## Dependencies and interactions

Smart Training interacts with Trackblazer native decision scoring, training blacklists, failure thresholds, summer priority, skill-hint priority, and item usage decisions such as Good-Luck Charm and Reset Whistle.

## Verification

Run a turn with high-bond partners on a training command and confirm the decision trace includes rainbow/friendship reasons. At full HP, verify Wit is not selected solely for recovery unless a configured rainbow exception applies.
