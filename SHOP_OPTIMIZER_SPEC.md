# SHOP_OPTIMIZER_SPEC.md — Self-Tuning Shop Policy Optimizer

A two-layer system for optimizing shop purchases and item usage in a umamusume
career bot. All configuration changes are driven by a **deterministic numeric
optimizer** that reads past career records and updates settings automatically.
A language model (LLM) is a secondary layer — invoked only for exception handling
and human-readable explanation, never for configuration decisions.

---

## Scope

This system applies **only to shop and inventory decisions** — when to buy items,
which items to prioritize, when to use items, and how to avoid wasting them by
the end of a career.

It does **not** apply to race selection or race execution. Those decisions are
handled by the bot's auto solver, which already has its own logic for picking
races, choosing running styles, and managing race chains. This system is a second
layer that sits on top of that solver and focuses exclusively on the shop.

---

## Glossary

| Term | Meaning |
|---|---|
| Career | One full playthrough from the trainee's debut to the final Climax races. Typically 77–78 turns long. |
| Turn | One unit of in-game time. Each turn the bot takes exactly one action. |
| Skill Points | The currency used to purchase skills for the trainee. Written as "Skill Points" throughout this document. |
| Mood | The trainee's current motivation level. Five levels, from worst to best: Awful, Bad, Normal, Good, Great. Affects both training efficiency and race attribute performance. |
| Stats | The five trainee attributes: Speed, Stamina, Power, Guts, and Wit. |
| Energy (Vitality) | The trainee's current stamina bar for training. Depletes from training, recovers from rest and energy items. Separate from the Stamina stat. |
| Shop | The in-game store where items are purchased using coins. Available on most turns. |
| Coins | The currency used to buy items from the shop. |
| Inventory | Items the bot currently holds. Items stay in inventory until consumed or the career ends. |
| Final Inventory | Items still in inventory at career end. Every item here is waste — coins and turns spent acquiring something that never helped. |
| Bootcamp | The summer training camp. Occurs at two fixed windows: turns 37–40 (first) and turns 61–64 (second). These 8 turns are the highest-value training turns in the career. Motivating Megaphones, Empowering Megaphones, and Ankle Weights for the matching stat should all be active simultaneously during bootcamp. |
| Climax | The final arc of the career, beginning after turn 73. Contains up to 3 Climax races at approximately turns 74, 76, and 78. The career ends when the last Climax race runs. |
| Climax Race 1 | The first Climax race, at approximately turn 74. Every career reaches this race. |
| Climax Race 2 | The second Climax race, at approximately turn 76. Most careers reach this race. |
| Climax Race 3 | The third and final Climax race, at approximately turn 78. Some careers end at turn 76 without reaching this race — the most common cause of Master Cleat Hammer over-reservation. |
| Grade 1 Race | The highest tier of regular races. |
| Running Style | How the trainee positions during a race: Front Runner, Pace Chaser, Late Surger, or End Closer. |
| Bond / Friendship | How close a support card's friendship gauge is to the trainee. When the gauge reaches 80%+ (shown orange), the support card is eligible to trigger Friendship Training — a training turn with a rainbow glow that gives significantly larger stat gains. |
| Friendship Training | A training turn where one or more support cards at 80%+ bond are present. Gives significantly more stats than normal training. High-Energy items are worth using before turns with multiple stacked Friendship Trainings to prevent injury from low Energy. |
| Support Cards | A deck of 6 cards selected before the career. They determine which stat trainers appear each turn, provide skill hints, and trigger random events. |
| Ailment | A negative status effect on the trainee (Night Owl, Slacker, Skin Outbreak, Slow Metabolism, Migraine, Practice Poor). Each has exactly one cure item. |
| Instant-Use Item | An item consumed immediately when purchased, on the same turn. Never sits in inventory. Cannot be wasted. |
| Held Item | An item that goes into inventory when purchased and must be triggered manually or automatically by a rule. These can become waste. |
| Dump Window | A late-career period (usually after turn 60–65) where the bot relaxes buying restrictions and tries to spend remaining coins before the career ends. |
| Optimizer | The deterministic function that reads numeric career records and outputs an updated settings vector. No language model component. |

### Mood Effects Reference

| Mood | Training Efficiency | Attribute Bonus During Race |
|---|---|---|
| Great | +20% | +4% |
| Good | +10% | +2% |
| Normal | No change | No change |
| Bad | −10% | −2% |
| Awful | −20% | −4% |

Mood is the single most impactful variable the bot can influence through item use.
Entering the Climax arc in Bad or Awful mood means every Climax race runs at a
2–4% stat penalty. This is why Mood repair items (Plain Cupcakes, Berry Sweet
Cupcakes) are treated as high-priority purchases when mood is declining toward Bad.

---

## Item Reference

### Energy and Vitality Items

| Item | Energy Restored | Cost |
|---|---|---|
| Vita 20 | 20 | 35 coins |
| Vita 40 | 40 | 55 coins |
| Vita 65 | 65 | 75 coins |
| Royal Kale Juice | Full recovery | 70 coins |
| Energy Drink MAX | 5 (emergency only) | 30 coins |
| Energy Drink MAX EX | Full recovery | 50 coins |

### Mood Items

| Item | Effect |
|---|---|
| Plain Cupcake | Repairs bad Mood. Synergizes with Royal Kale Juice (use together). |
| Berry Sweet Cupcake | Stronger Mood repair. |
| Yummy Cat Food | Instant-use Mood boost. Consumed on purchase. |

### Stat Consumables (all instant-use)

| Item | Stat Gained |
|---|---|
| Speed/Stamina/Power/Guts/Wit Notepad | +small points to named stat |
| Speed/Stamina/Power/Guts/Wit Manual | +medium points to named stat |
| Speed/Stamina/Power/Guts/Wit Scroll | +large points to named stat |
| Grilled Carrots | Instant-use, adds to a stat and bond. |

### Race-Use Items (Hammers and Glow Sticks)

| Item | Use Case |
|---|---|
| Master Cleat Hammer | Used before Grade 1 and Climax races for a large performance boost. The most valuable pre-race item. |
| Artisan Cleat Hammer | Fallback when no Master Cleat Hammer is available. Used before Grade 2 races. |
| Glow Sticks | Used before high-fan-value races when the fan count is above the minimum threshold. |

### Training Amplifiers

| Item | Effect |
|---|---|
| Motivating Megaphone | Large training bonus. Best used during bootcamp. |
| Empowering Megaphone | Large training bonus. Best used during bootcamp. |
| Coaching Megaphone | Training bonus, but affects a different part of the formula. |
| Speed/Stamina/Power/Guts Ankle Weights | Held item. Adds a bonus to the matching stat on each training turn until consumed. |
| Reset Whistle | Rerolls the current training selection when the best available training is poor. |
| Good-Luck Charm | Reduces the penalty for failed training attempts. Used before uncertain turns. |

### One-Time Permanent Buffs (all instant-use)

Pretty Mirror, Reporter's Binoculars, Master Practice Guide, Scholar's Hat —
each applies an immediate permanent bonus. Never wasted.

### Ailment Cures

| Ailment | Cure Item |
|---|---|
| Night Owl | Fluffy Pillow |
| Slacker | Pocket Planner |
| Skin Outbreak | Rich Hand Cream |
| Slow Metabolism | Smart Scale |
| Migraine | Aroma Diffuser |
| Practice Poor | Practice Drills DVD |
| Any ailment | Miracle Cure |

---

## What Problem This System Solves

The bot's shop logic runs one turn at a time. It cannot look backwards and say:
"In the last 15 careers, every time `climax_master_hammer_reserve` was set to 3
but fewer than 3 Climax races ran, the waste flag fired — the reserve should be 2."

That backward-looking pattern recognition requires memory across careers. Storing
it as text and asking a language model to interpret it each time is unreliable —
LLMs can hallucinate, drift, and cannot be tested deterministically. Instead, this
system stores every career as a **flat numeric record** and runs a deterministic
optimizer over those records. The optimizer detects which settings values correlate
with waste flags firing and adjusts them toward values where waste flags do not fire.
No language model is in the critical path.

### Two Layers

**Layer 1 — The Optimizer (primary, automated):**
A deterministic function. Reads the numeric career record database. Computes
correlations between settings values and waste flag outcomes. Outputs a new
settings vector with specific integer values. Runs automatically after every career.
No human input required. No text. No interpretation.

**Layer 2 — The LLM (secondary, exception-triggered):**
A language model. Only invoked when: (a) the optimizer produces a regression —
Item Execution score drops more than 2 points below the prior 3-career mean;
(b) a novel waste flag combination appears with no matching past records; or
(c) a human explicitly requests an explanation. The LLM produces human-readable
text only. It never writes config values.

The optimizer gradually moves settings toward lower-waste ranges observed in prior
careers. It is expected to improve shop behavior over repeated runs, but it does
not prove global optimality. It cannot evaluate whether the bot is buying the
*best* items or simply *fewer* items.

---

## Connecting a Bot to This System

### The Universal Shop Profile (Common Language)

Different bots store their shop settings under different internal names, in
different formats. This system requires every connected bot to translate its
internal settings into a **Universal Shop Profile** before submitting a career
record. Think of it as currency exchange — the Universal Shop Profile is the
common format every bot uses when talking to the optimizer.

When the optimizer outputs an updated settings vector, it outputs it in Universal
Shop Profile format. Each bot translates those values back into its own internal
config. The optimizer never knows or cares what internal names a bot uses.

### Universal Shop Profile Fields

| Field Name | Type | Meaning |
|---|---|---|
| `energy_buy_threshold` | Integer 0–100 | Energy level below which the bot considers buying an energy item |
| `climax_master_hammer_reserve` | Integer | How many Master Cleat Hammers to hold back for Climax races |
| `climax_artisan_hammer_reserve` | Integer | How many Artisan Cleat Hammers to hold as a fallback for Climax |
| `master_hammer_buy_cap_turn` | Integer | Turn after which the bot stops buying new Master Cleat Hammers |
| `glow_sticks_min_fans` | Integer | Minimum fan count before Glow Sticks are considered for use |
| `bootcamp_strong_mega_target` | Integer | How many Motivating or Empowering Megaphones to hold going into bootcamp |
| `coaching_mega_enabled` | Integer 0 or 1 | Whether the bot is allowed to buy Coaching Megaphones (1 = yes, 0 = no) |
| `skill_point_buy_threshold` | Integer | Skill Points must be above this before any skill purchase is considered |
| `skill_point_hoard_threshold` | Integer | Buy skills immediately if Skill Points exceed this, without waiting for the force turn |
| `skill_point_force_turn` | Integer | Turn at which the bot forces skill purchases regardless of Skill Point level |
| `skill_point_floor` | Integer | Minimum Skill Points required for the force-buy to trigger (prevents buying at 0) |
| `dump_window_start_turn` | Integer | Turn at which the bot enters the dump window and relaxes buying restrictions |
| `late_game_save_items` | Integer 0 or 1 | Whether the bot holds items back during the dump window (1) or spends aggressively (0) |
| `ankle_weights_max_stock` | Integer | Maximum Ankle Weights of one type to hold in inventory at once |

**Critical warning:** If `skill_point_hoard_threshold` and `skill_point_floor` are
both set above realistic mid-career Skill Point levels, neither skill-buying trigger
can fire. This causes the bot to finish with all Skill Points unspent. The optimizer
detects this when `skill_buy_failure = 1` co-occurs with both thresholds above their
safe ranges and adjusts them downward.

### How a Bot Connects

1. At career start, the bot translates its internal settings into the Universal Shop
   Profile and records the active values as the settings vector.
2. At career end, the bot writes the completed numeric career record to the database.
3. The optimizer reads the last N non-human-directed records and computes the new
   settings vector.
4. The bot translates the new settings vector back to its internal config before
   the next career starts.

---

## The Numeric Career Record

Every career is stored as a flat numeric record. No free-text fields in the analysis
path. All values are integers or 0/1 flags.

### Settings Vector

The Universal Shop Profile values active during this career. All integers.

### Outcomes Vector

| Field | Type | Description |
|---|---|---|
| `item_execution_score` | Integer 0–20 | Computed item use efficiency score (see Run Score section) |
| `sp_remaining` | Integer | Skill Points at career end |
| `coins_remaining` | Integer | Coins at career end |
| `waste_coin_value` | Integer | Estimated coin value of all items in final inventory |
| `climax_mood` | Integer 1–5 | Mood level at Climax entry (1=Awful, 2=Bad, 3=Normal, 4=Good, 5=Great) |
| `sp_t40` | Integer | Skill Points at turn 40 |
| `sp_t50` | Integer | Skill Points at turn 50 |
| `sp_t60` | Integer | Skill Points at turn 60 |
| `sp_t70` | Integer | Skill Points at turn 70 |
| `coins_t37` | Integer | Coins at turn 37 (first bootcamp entry) |
| `coins_t60` | Integer | Coins at turn 60 (second bootcamp entry) |
| `skills_purchased` | Integer | Number of skills bought during the career |
| `climax_races_run` | Integer | Number of Climax races that actually ran (1, 2, or 3) |
| `total_items_bought` | Integer | Total items purchased during the career |
| `total_items_used` | Integer | Total items consumed (not wasted) during the career |
| `bootcamp_megas_used` | Integer | Megaphones used on bootcamp turns |
| `bootcamp_ankles_used` | Integer | Ankle Weights active on bootcamp turns |

### Waste Flag Vector

All fields are 0 or 1. A flag set to 1 means the waste condition occurred.

**Item Leftovers**

| Flag | Set to 1 when |
|---|---|
| `skill_point_hoard` | Skill Points remaining at career end exceeded 50 |
| `skill_buy_failure` | Zero skills were purchased during the entire career |
| `master_cleat_waste` | Master Cleat Hammers in final inventory |
| `artisan_cleat_waste` | Artisan Cleat Hammers in final inventory |
| `vita_waste` | Any Vita 20, Vita 40, or Vita 65 in final inventory |
| `megaphone_waste` | Any Motivating or Empowering Megaphone in final inventory after turn 65 |
| `ankle_weights_waste` | Any Ankle Weights in final inventory |
| `reset_whistle_waste` | Reset Whistles in final inventory |
| `good_luck_charm_waste` | Good-Luck Charms in final inventory |
| `coin_hoard` | More than 50 coins remaining at career end |

**Timing and Allocation Errors**

| Flag | Set to 1 when |
|---|---|
| `bootcamp_mega_shortage` | Fewer Megaphones available at bootcamp entry than the target |
| `climax_hammer_excess` | More Master Cleat Hammers reserved than Climax races that actually ran |
| `sp_catchall_blocked` | Both `skill_point_hoard_threshold` and `skill_point_floor` were above realistic mid-career Skill Point levels simultaneously, blocking all skill buying |
| `vita_never_triggered` | Vita items were purchased but the energy threshold was never breached |

**Vita Diagnostic Flags** (more specific than `vita_waste`)

| Flag | Set to 1 when |
|---|---|
| `vita_bought_too_early` | Vita items were purchased before turn 20 and sat in inventory more than 30 turns before use |
| `vita_used_on_low_value_turn` | Vita items were used on a turn with no Friendship Training and no bootcamp adjacency |
| `vita_missing_before_high_value_training` | Energy was below 50 before a Friendship Training turn but no Vita item was available in inventory |

**Ankle Weights Diagnostic Flags** (more specific than `ankle_weights_waste`)

| Flag | Set to 1 when |
|---|---|
| `ankle_weights_held_past_bootcamp` | Ankle Weights remained in inventory after the second bootcamp ended (turn 64) |
| `ankle_weights_wrong_stat` | Ankle Weights held for a stat not trained by any support card in the current deck |
| `ankle_weights_no_matching_training` | Ankle Weights were held but the matching training stat never appeared on a turn where training was taken |
| `ankle_weights_used_without_mega` | Ankle Weights were active during bootcamp but no Megaphone was also active on those turns |
| `ankle_weights_stock_cap_blocked` | `ankle_weights_max_stock` prevented buying an Ankle Weight on a turn when the matching training appeared |

### Human Direction Flag

| Field | Type | Description |
|---|---|---|
| `human_directed` | Integer 0 or 1 | Set to 1 if any manual priority rating was non-zero or any value override was active. Records with `human_directed = 1` are excluded from optimizer input. |

### Human Annotation (Optional)

A free-text notes field may be attached by a human after the career ends. It is
not read by the optimizer. It exists solely so a human reviewing the LLM's
exception output can attach context for their own reference.

---

## Turn-Level Shop Log

One record per turn where the shop was available, written during the career. The
optimizer reads only career records. Turn-level logs are the diagnostic layer
beneath — used by the LLM exception handler and human reviewers to explain what
the career record numbers cannot.

Without turn-level context the optimizer cannot tell the difference between
"the bot failed to buy megaphones" vs "the shop never offered megaphones" vs
"the bot skipped shop because training was too valuable" vs "the bot bought
megaphones but mistimed usage." The career record is enough for scoring. Turn
logs are needed for root cause.

### Core Context Fields

| Field | Type | Description |
|---|---|---|
| `career_id` | String | Links this turn record to its career record |
| `turn` | Integer | Turn number (1–78) |
| `shop_available` | Integer 0 or 1 | Whether the shop was accessible this turn |
| `shop_visited` | Integer 0 or 1 | Whether the bot entered the shop |

### Game State at Turn Start

| Field | Type | Description |
|---|---|---|
| `energy` | Integer 0–100 | Trainee energy at turn start |
| `mood` | Integer 1–5 | Mood at turn start |
| `coins` | Integer | Coins available at turn start |
| `skill_points` | Integer | Skill Points at turn start |
| `ailment_active` | Integer 0 or 1 | Whether a trainee ailment is currently active |
| `ailment_type` | String or null | Which ailment, or null |

### Bootcamp and Race Context

| Field | Type | Description |
|---|---|---|
| `turns_to_bootcamp1` | Integer | Turns until first bootcamp (negative if past it) |
| `turns_to_bootcamp2` | Integer | Turns until second bootcamp (negative if past it) |
| `in_bootcamp` | Integer 0 or 1 | Whether this turn is one of the 8 bootcamp turns |
| `race_next_turn` | Integer 0 or 1 | Whether a race occurs next turn |
| `race_grade` | Integer or null | Grade of the next race (1, 2, or 3) or null |
| `turns_to_climax1` | Integer | Turns until Climax Race 1 |
| `in_dump_window` | Integer 0 or 1 | Whether the bot is currently in the dump window |

### Training Context

| Field | Type | Description |
|---|---|---|
| `best_training_score` | Integer | Highest-scoring available training option this turn |
| `friendship_training_available` | Integer 0 or 1 | Whether any support card at 80%+ bond is present |
| `friendship_cards_count` | Integer | How many support cards are at 80%+ bond this turn |
| `training_taken` | Integer 0 or 1 | Whether the bot chose training over shop this turn |
| `training_taken_stat` | String or null | Stat trained, or null |

### Inventory at Turn Start

| Field | Type | Description |
|---|---|---|
| `inv_master_hammers` | Integer | Master Cleat Hammers in inventory |
| `inv_artisan_hammers` | Integer | Artisan Cleat Hammers in inventory |
| `inv_vita_items` | Integer | Total Vita items in inventory |
| `inv_strong_megaphones` | Integer | Motivating + Empowering Megaphones in inventory |
| `inv_coaching_megaphones` | Integer | Coaching Megaphones in inventory |
| `inv_ankle_weights` | Integer | Total Ankle Weights in inventory |
| `inv_glow_sticks` | Integer | Glow Sticks in inventory |
| `inv_mood_items` | Integer | Plain Cupcakes + Berry Sweet Cupcakes in inventory |

### Purchase and Skip Decision

| Field | Type | Description |
|---|---|---|
| `shop_items_offered` | JSON array | Item names offered in the shop this turn |
| `item_bought` | String or null | Name of item purchased, or null |
| `item_bought_cost` | Integer | Coin cost of purchased item, or 0 |
| `skip_reason` | String or null | Reason code if shop was skipped (see table below) |
| `item_used_this_turn` | String or null | Name of held item triggered this turn, or null |
| `item_used_context` | String or null | Context code for why item was used (see table below) |

### Skip Reason Codes

| Code | Meaning |
|---|---|
| `training_priority` | Training scored higher than any shop action |
| `friendship_training` | Friendship Training was available — skipping shop was correct |
| `insufficient_coins` | Could not afford the most useful available item |
| `inventory_full_category` | Already at stock cap for the item category being offered |
| `not_needed` | No offered item addressed a current need |
| `race_turn` | Race turn; shop was skipped for race prep |
| `dump_window_skip` | Dump window active but no high-priority items offered |
| `none` | Purchase was made (not a skip) |

### Item Use Context Codes

| Code | Meaning |
|---|---|
| `pre_race_hammer` | Master Cleat Hammer or Artisan Hammer used before a race |
| `pre_race_glow` | Glow Stick used before a high-fan race |
| `energy_threshold` | Energy dropped below `energy_buy_threshold`; Vita item triggered |
| `bootcamp_mega` | Megaphone used on a bootcamp turn |
| `bootcamp_ankle` | Ankle Weights active on a bootcamp turn |
| `mood_repair` | Cupcake used to repair declining mood |
| `ailment_cure` | Ailment cure item used |
| `emergency_energy` | Energy Drink MAX used (energy critically low) |
| `dump_window_use` | Item used during dump window to clear inventory |

---

## How the Optimizer Works

### Tiered Adjustment by Record Count

The optimizer's behavior scales with how many eligible records exist. A small
number of noisy early careers should not drive large corrections.

| Eligible Records | Behavior |
|---|---|
| 0–2 | Collect only. No adjustment made. Output current settings unchanged. |
| 3–4 | Micro-adjustments. Step size capped at 5% per cycle. |
| 5–9 | Small adjustments. Step size capped at 10% per cycle. |
| 10–19 | Normal adjustments. 15% step limit applies. |
| 20+ | Full confidence. 15% step limit applies. |

### Step 1: Compute Flag Rates per Settings Value

For each waste flag and each settings field, the optimizer groups past records by
the settings field's value and computes the rate at which that flag fires.

**Example — `climax_master_hammer_reserve` vs `climax_hammer_excess`:**

| `climax_master_hammer_reserve` | `climax_hammer_excess` flag rate (last 6 careers) |
|---|---|
| 3 | 4 out of 4 careers (100%) |
| 2 | 0 out of 2 careers (0%) |

The optimizer reads: value 3 → flag fires 100% of the time. Adjustment direction:
decrease toward 2.

Note: single-field correlations can be misleading. The same waste flag can be
caused by multiple fields interacting — for example, `climax_hammer_excess` may
be caused by `climax_master_hammer_reserve` too high, OR `master_hammer_buy_cap_turn`
too late, OR an unusually low `climax_races_run`. The optimizer adjusts the most
directly correlated field. When a regression occurs, the LLM exception handler
can surface multi-field interactions (see LLM Exception Layer section).

**Example — `skill_point_hoard_threshold` vs `skill_buy_failure`:**

| `skill_point_hoard_threshold` | `skill_point_floor` | `skill_buy_failure` rate |
|---|---|---|
| ≥ 1400 | ≥ 1000 | 3 out of 3 careers (100%) |
| ≤ 1000 | ≤ 500 | 0 out of 3 careers (0%) |

### Step 2: Compute Adjustment

For each settings field where a misconfigured value is detected:

```
qualified_clean = careers where:
    — all waste flags = 0
    — item_execution_score ≥ 15
    — skills_purchased ≥ 1
    — bootcamp_mega_shortage = 0

clean_mean   = mean value of that field across qualified_clean careers
current      = current active value of that field
step_limit   = tier table above (5%, 10%, or 15%)
step         = (clean_mean - current) × step_limit
new_value    = round(current + step)
new_value    = clamp(new_value, guardrail_min, guardrail_max)
```

The "clean career" definition requires adequate item use, not just absence of
waste. A career where the bot bought nothing would show no waste flags but would
not qualify because `skills_purchased = 0`. This prevents the optimizer from
drifting toward "buy less" as the solution to all waste.

### Step 3: Apply Guardrails

The optimizer is never allowed to set a field outside its safe range. These limits
prevent a noisy early career from driving settings to an absurd value.

| Field | Min | Max |
|---|---|---|
| `energy_buy_threshold` | 20 | 70 |
| `climax_master_hammer_reserve` | 1 | 3 |
| `climax_artisan_hammer_reserve` | 0 | 2 |
| `master_hammer_buy_cap_turn` | 55 | 72 |
| `bootcamp_strong_mega_target` | 1 | 4 |
| `skill_point_buy_threshold` | 100 | 800 |
| `skill_point_hoard_threshold` | 600 | 1400 |
| `skill_point_force_turn` | 50 | 70 |
| `skill_point_floor` | 100 | 800 |
| `dump_window_start_turn` | 55 | 68 |
| `ankle_weights_max_stock` | 0 | 2 |

If the computed new value falls outside the range, it is clamped to the nearest
limit. The clamping event is logged so a human can review it.

### Step 4: Output

The optimizer outputs a complete settings vector. Fields with no misconfiguration
detected are unchanged from current values. This vector is applied directly before
the next career.

No text. No explanation. Just numbers.

---

## Manual Direction Input

The human operator can submit numerical overrides to pin specific settings or shift
the optimizer's starting point. These are numbers only — the optimizer reads them
directly without interpretation.

### Priority Ratings

Priority ratings adjust the optimizer's step size for a dimension.

| Rating | Effect on step size |
|---|---|
| +2 | Step × 2.0 (move twice as fast toward optimal) |
| +1 | Step × 1.5 |
|  0 | Default step (no modification) |
| -1 | Step × 0.5 (move half as fast) |
| -2 | Step × 0 (freeze — optimizer makes no adjustment this cycle) |

| Dimension | What it controls |
|---|---|
| `energy_priority` | Adjustment speed for `energy_buy_threshold` |
| `mood_priority` | Adjustment speed for mood-related thresholds |
| `bootcamp_mega_priority` | Adjustment speed for `bootcamp_strong_mega_target` |
| `hammer_conservation` | Adjustment speed for `climax_master_hammer_reserve` |
| `skill_spending_urgency` | Adjustment speed for skill-point thresholds and force turn |
| `dump_aggression` | Adjustment speed for `dump_window_start_turn` and `late_game_save_items` |
| `ankle_weights_priority` | Adjustment speed for `ankle_weights_max_stock` |
| `coaching_mega_priority` | Adjustment speed for `coaching_mega_enabled` |

Example priority rating input:
```
energy_priority: -1
mood_priority: +2
bootcamp_mega_priority: +1
hammer_conservation: 0
skill_spending_urgency: +1
dump_aggression: 0
ankle_weights_priority: 0
coaching_mega_priority: -2
```

### Value Overrides

These pin a specific field to an exact value for the next career, bypassing the
optimizer's output for that field. The career that runs with a value override is
marked `human_directed = 1` and excluded from the optimizer's input pool.

| Override Field | Example | Effect |
|---|---|---|
| `climax_master_hammer_reserve` | `= 2` | Hold exactly 2 Master Cleat Hammers for Climax |
| `climax_artisan_hammer_reserve` | `= 1` | Hold exactly 1 Artisan Cleat Hammer as fallback |
| `bootcamp_strong_mega_target` | `= 3` | Hold exactly 3 strong Megaphones going into bootcamp |
| `skill_point_force_turn` | `= 55` | Force Skill Point spending at turn 55 |
| `dump_window_start_turn` | `= 62` | Start the dump window at turn 62 |
| `master_hammer_buy_cap_turn` | `= 60` | Stop buying new Master Cleat Hammers after turn 60 |

Value overrides take precedence over priority ratings. If both are set for the
same field, the value is used and the rating has no additional effect.

### What Overrides Cannot Do

- Override the auto solver's race decisions.
- Override emergency energy use — if the trainee has zero Energy before a
  mandatory race, an energy item is used regardless of any rating.
- Override running style selection.

---

## The Run Score for Shop Performance

Each career receives a numeric Item Execution score (0–20) stored in the outcomes
vector. This is the optimizer's primary signal.

- Base: items consumed ÷ items purchased, weighted by item coin value
- Master Cleat Hammers and Vita items carry higher weight than Reset Whistles
  or Good-Luck Charms
- Zero Master Cleat Hammers or Vita items in final inventory = full sub-score
  for those categories
- Each Motivating or Empowering Megaphone in final inventory after turn 65
  applies a heavy deduction

A career that bought 20 items and used all 20 scores higher than one that bought
30 items and used 25. The optimizer treats buying less and using all of it as
strictly better than buying more and wasting some.

**Regression detection:** If the 3-career rolling mean of `item_execution_score`
drops more than 2 points after an optimizer adjustment, the LLM exception handler
is triggered.

---

## The Automated Feedback Loop

```
Career completes
      │
      ▼
Numeric record written to database
(settings vector + outcomes vector + waste flag vector, all integers)
human_directed flag set based on whether any manual input was active
      │
      ▼
  human_directed = 1?
      │
      ├── YES → record stored but excluded from optimizer input
      │         career outcome still visible in history for human review
      │
      └── NO  → record enters optimizer input pool
                │
                ▼
          Optimizer runs
          Checks eligible record count → applies tier step limit
          For each settings field:
            — compute waste flag rate at current value
            — compute adjustment step toward qualified clean-career mean
            — apply tier step limit
            — clamp to guardrail min/max
          Output: new settings vector (integers)
                │
                ▼
          New settings applied before next career
                │
                ▼
          Regression check: 3-career rolling mean of item_execution_score
                │
                ├── Score dropped > 2 points from prior mean
                │         → Exception: LLM invoked (see LLM Exception Layer)
                │         → LLM identifies which setting changed and what
                │           the data showed
                │         → Human can apply a value override to correct it
                │           or accept the adjustment and wait for more data
                │
                └── Score stable or improved
                          → No action. Loop continues.
```

Human involvement is only triggered by regressions or novel flag combinations.
The optimizer runs silently every career otherwise.

---

## LLM Exception Layer

The LLM is a secondary tool. It is not consulted on routine careers.

### When the LLM Is Invoked

Three conditions trigger the LLM. All are exceptional — most careers produce none.

- **Regression:** The 3-career rolling mean of `item_execution_score` drops more
  than 2 points after an optimizer adjustment.
- **Novel Flag Combination:** A waste flag combination appears that has no matching
  pattern in the past record database. The optimizer cannot compute an adjustment
  step for a combination it has never seen.
- **Human-Requested Explanation:** A human explicitly requests a plain-language
  explanation of a past career's outcomes, a specific waste flag, or why a settings
  adjustment was made.

### What the LLM Receives

When invoked, the LLM receives a structured prompt containing:

1. The trigger reason and which career caused it.
2. The full numeric career record for the triggering career.
3. The last 5 eligible career records, for comparison.
4. The settings diff — which fields the optimizer changed and by how much.
5. Turn-level shop logs for the triggering career.
6. The current optimizer guardrails.

All data passed to the LLM is numeric. No raw game text, no UI strings, no
free-form human annotation notes are included in the analysis prompt.

### What the LLM May Output

The LLM output is plain text for human consumption only. Acceptable outputs:
- An explanation of which setting changed and what the data showed.
- Identification of which turn the waste decision appears to have been made and
  what context surrounded it.
- A suggested manual override value the human *may choose to apply*. Framed as
  a suggestion only — the human decides.
- A description of a novel flag combination and why the optimizer cannot handle it.

### What the LLM Must Never Do

- **Never write configuration values directly.** The optimizer is the sole source
  of config updates. If a suggested value is applied, the human applies it as a
  manual override, which marks the career `human_directed = 1`.
- **Never be consulted on routine careers.** Running it every career introduces
  interpretation variability where determinism is available.
- **Never override the optimizer.** If the LLM and optimizer disagree, the human
  resolves it.
- **Never promote human-directed runs as evidence of optimal settings.** A run
  where a human forced specific behavior is excluded from the optimizer's input pool.
- **Never clear past failure records.** Records where waste flags fired are the
  most valuable records in the database.
- **Never conflate instant-use items with held items when measuring waste.**
  Instant-use items cannot be wasted. Waste analysis only applies to held items.

### LLM Backend Configuration

Three backends are supported, checked in this priority order:
**endpoint** → **codex** → **ollama**. The first one that is configured and
reachable is used.

```json
{
  "llm_backend": "codex",
  "codex_api_key": "sk-...",
  "codex_plan_tier": "pro",
  "ollama_host": "http://localhost:11434",
  "ollama_model": "llama3.2:8b",
  "endpoint_url": null,
  "endpoint_api_key": null
}
```

| Field | Type | Description |
|---|---|---|
| `llm_backend` | String | Active backend: `"codex"`, `"ollama"`, or `"endpoint"` |
| `codex_api_key` | String | API key for the Codex cloud service |
| `codex_plan_tier` | String | `"free"`, `"basic"`, `"pro"`, or `"enterprise"`. Drives automatic model selection. |
| `ollama_host` | String | Base URL of the Ollama instance. Defaults to `http://localhost:11434`. |
| `ollama_model` | String | Model name from `ollama list`. Required when backend is `"ollama"`. |
| `endpoint_url` | String or null | Full URL of a custom HTTP endpoint. If set, overrides all other backends. |
| `endpoint_api_key` | String or null | Optional bearer token for the custom endpoint. |

**Codex:** The system queries the API for models available under the plan and
selects the most capable one. It does not hardcode model names — the tier drives
selection so the config does not need updating when new models are released.

**Ollama:** The model name must match exactly as it appears in `ollama list`
(e.g., `llama3.2:8b`, `deepseek-r1:32b`). The system uses this name verbatim
in every API call and does not validate or discover models at runtime.

**Endpoint:** The system sends a POST request with `{"prompt": "...", "max_tokens": 512}`.
If `endpoint_api_key` is provided, it is sent as a bearer token. The endpoint must
return a `text` or `content` field with the generated string.

**Fallback:** If the active backend is unavailable, the system tries the next in
priority order. If all backends fail, the exception handler logs `"llm_unavailable"`
in the human annotation field and the optimizer's numeric output is applied unchanged.
A failed LLM invocation does not block the optimizer or the next career.

---

## Exportable Knowledge Packs

### The Problem With Starting From Zero

A new user with an empty record database cannot run the optimizer — it requires
at least 3 eligible records, and even with 3 records the adjustments are intentionally
tiny. During those first careers the bot runs on defaults, potentially repeating
mistakes the community already solved.

### What a Knowledge Pack Is

A pre-seeded safe-range table derived from community career records, stripped of
personal data. Contains no raw records — only the numeric safe ranges the optimizer
can use as a starting point before local records exist.

**1. Safe Starting Ranges**

For each Universal Shop Profile field, the value range that has produced
`item_execution_score` ≥ 15 across confirmed non-human-directed careers from
contributing users.

```json
{
  "energy_buy_threshold":         { "min": 35, "max": 50 },
  "climax_master_hammer_reserve": { "min": 2,  "max": 3  },
  "bootcamp_strong_mega_target":  { "min": 2,  "max": 3  },
  "skill_point_hoard_threshold":  { "min": 800,"max": 1200},
  "skill_point_force_turn":       { "min": 55, "max": 65  }
}
```

**2. Known Failure Conditions**

Settings combinations that have produced a specific waste flag in 3 or more
independent careers. Stored as numeric threshold conditions, not text.

```json
{
  "flag": "sp_catchall_blocked",
  "condition": {
    "skill_point_hoard_threshold": { "gte": 1400 },
    "skill_point_floor":           { "gte": 1000 }
  },
  "observed_in": 3,
  "adjustment": {
    "skill_point_hoard_threshold": 1000,
    "skill_point_floor": 500
  }
}
```

When a new user imports a Knowledge Pack, the optimizer initializes using the
safe starting ranges as its clean-career baseline. As local careers complete, local
data progressively replaces the imported baseline. A locally observed pattern with
3 confirmations outweighs the same pattern from an imported pack.

### What a Knowledge Pack Does NOT Contain

- Raw career records or turn-by-turn data
- Any information about which trainee, scenario, or support card deck was used
- Settings tested by only a single user or single career
- Records marked `human_directed = 1`
