# RAG_AI.md — Self-Optimizing Shop Configuration System

This document describes a two-layer system for optimizing shop purchases and item
usage in a umamusume career bot. All configuration changes are driven by a
**deterministic numeric optimizer** that reads past career records and updates
settings automatically. A language model (LLM) is a secondary layer — it is only
invoked for exception handling and human-readable explanation, never for
configuration decisions.

---

## Scope: What This Document Covers

This framework applies **only to shop and inventory decisions** — when to buy
items, which items to prioritize, when to use items, and how to avoid wasting
them by the end of a career.

It does **not** apply to race selection or race execution. Those decisions are
handled by the bot's auto solver, which already has its own logic for picking
races, choosing running styles, and managing race chains. This system is a second
layer that sits on top of that solver and focuses exclusively on the shop.

---

## Glossary

Terms used throughout this document, written out in full to avoid confusion.

| Term | Meaning |
|---|---|
| Career | One full playthrough from the trainee's debut to the final Climax races. Typically 77–78 turns long. |
| Turn | One unit of in-game time. Each turn the bot takes exactly one action. |
| Skill Points | The currency used to purchase skills for the trainee. Abbreviated SP only in this glossary — written as "Skill Points" everywhere else in this document. |
| Mood | The trainee's current motivation level. Five levels, from worst to best: Awful, Bad, Normal, Good, Great. Affects both training efficiency and race attribute performance. See table below. |
| Stats | The five trainee attributes: Speed, Stamina, Power, Guts, and Wit. |
| Energy (Vitality) | The trainee's current stamina bar for training. Depletes from training, recovers from rest and energy items. Separate from the Stamina stat. |
| Shop | The in-game store where items are purchased using coins. Available on most turns. |
| Coins | The currency used to buy items from the shop. |
| Inventory | Items the bot currently holds. Items stay in inventory until consumed or the career ends. |
| Final Inventory | Items still in inventory at career end. Every item here is waste — coins and turns spent acquiring something that never helped. |
| Bootcamp | The summer training camp. Occurs at two fixed windows during the career: the first bootcamp runs on turns 37, 38, 39, and 40; the second runs on turns 61, 62, 63, and 64. These 8 turns are the highest-value training turns in the entire career. Motivating Megaphones, Empowering Megaphones, and Ankle Weights (for the matching stat) should all be active simultaneously during bootcamp — using a Megaphone without any Ankle Weights active, or holding Ankle Weights past bootcamp with no Megaphone, are both waste patterns. |
| Climax | The final arc of the career, beginning after turn 73. Contains up to 3 Climax races at approximately turns 74, 76, and 78. The career ends when the last Climax race runs (turn 76 if only 2 Climax races occur, turn 78 if all 3 run). Master Cleat Hammers and Glow Sticks are the primary items reserved for use here. The number of Climax races that will actually run is not always known in advance — the bot should protect Master Cleat Hammers for the expected count but must not over-reserve if fewer races are confirmed. |
| Climax Race 1 | The first Climax race, occurring at approximately turn 74. This is the minimum Climax participation — every career reaches this race. |
| Climax Race 2 | The second Climax race, occurring at approximately turn 76. Most careers reach this race. |
| Climax Race 3 | The third and final Climax race, occurring at approximately turn 78. Some careers end at turn 76 without reaching this race, which is the most common cause of Master Cleat Hammer over-reservation. |
| Grade 1 Race | The highest tier of regular races. Winning these gives the most fans. |
| Grade 2 Race | Mid-tier races. |
| Grade 3 Race | Lowest tier of regular races. |
| Running Style | How the trainee positions during a race: Front Runner, Pace Chaser, Late Surger, or End Closer. |
| Bond / Friendship | How close a support card's friendship gauge is to the trainee. The gauge fills by 7 points each time you train on a turn where that support card is present, by 5 points from skill hint training, and by 5 or 10 points from support card events. When the gauge reaches 80% or higher (shown by the gauge turning orange), the support card is eligible to trigger Friendship Training — a training turn with a rainbow glow that gives significantly larger stat gains. Multiple support cards at 80%+ can stack, making that training turn extremely efficient. Bond matters to item decisions because turns with several cards at orange are too valuable to skip for a shop visit — the bot must weigh whether buying an item is worth losing a high-bond training turn. |
| Friendship Training | A training turn where one or more support cards at 80%+ bond are present, shown by a rainbow glow. Gives significantly more stats than normal training. The full formula is: (Base Training + Stat Bonus) × Growth Rate Bonus × Mood Effect × Training Effectiveness × Friendship Bonus × Participant Count Bonus (+5% per additional support present). Friendship Training can still fail if the trainee's Energy is low, causing injury — high-Energy items like Vita 40 or Vita 65 are worth using before a turn with multiple stacked Friendship Trainings to prevent failure. |
| Support Cards | A deck of 6 cards selected before the career that act as the trainee's trainers and mentors. They determine which stat trainers appear on each turn, provide skill hints, and trigger random events that give energy or rare skills. There are 7 types: **Speed** (specializes in Speed — the most critical stat for race performance), **Stamina** (boosts Stamina to prevent running out of endurance mid-race), **Power** (boosts Power for overtaking and pushing through crowds at the finish), **Guts** (increases Guts for endurance in last-sprint situations), **Wisdom** (also called Wit in some bots — reduces training fatigue, prevents race debuffs, and helps skills trigger in races), **Friend** (not tied to a specific stat — focuses on keeping mood high, recovering energy, and boosting training effectiveness overall), and **Group** (similar to Friend, but features multiple trainees — gives varied stat gains, energy recovery, and exclusive events). The deck composition directly affects which stats grow fastest and which Friendship Training turns are highest value. |
| Ailment | A negative status effect on the trainee (Night Owl, Slacker, Skin Outbreak, Slow Metabolism, Migraine, Practice Poor). Each has a specific cure item. |
| Instant-Use Item | An item that is consumed immediately when purchased, on the same turn. It never sits in inventory. |
| Held Item | An item that goes into inventory when purchased and must be manually triggered or automatically triggered by a rule. These can become waste. |
| Dump Window | A late-career period (usually after turn 60–65) where the bot relaxes its buying restrictions and tries to spend remaining coins on useful items before the career ends. |
| Optimizer | The deterministic function that reads numeric career records and outputs an updated settings vector. Runs automatically after each career. Has no language model component. |

### Mood Effects Reference

| Mood | Training Efficiency | Attribute Bonus During Race |
|---|---|---|
| Great | +20% | +4% |
| Good | +10% | +2% |
| Normal | No change | No change |
| Bad | −10% | −2% |
| Awful | −20% | −4% |

Mood is the single most impactful variable the bot can influence through item
use. Entering the Climax arc in Bad or Awful mood means every Climax race runs
at a 2–4% stat penalty. Entering in Great mood means a 4% bonus. This is why
Mood repair items (Plain Cupcakes, Berry Sweet Cupcakes) are treated as
high-priority purchases when mood is declining toward Bad.

---

## Item Reference

All items in this section use their exact in-game names.

### Energy and Vitality Items
These restore the trainee's Energy bar. They sit in inventory until the bot
decides energy recovery is needed.

| Item | Energy Restored | Cost |
|---|---|---|
| Vita 20 | 20 | 35 coins |
| Vita 40 | 40 | 55 coins |
| Vita 65 | 65 | 75 coins |
| Royal Kale Juice | Full recovery | 70 coins |
| Energy Drink MAX | 5 (emergency only) | 30 coins |
| Energy Drink MAX EX | Full recovery | 50 coins |

### Mood Items
These affect the trainee's Mood (motivation level).

| Item | Effect |
|---|---|
| Plain Cupcake | Repairs bad Mood. Synergizes with Royal Kale Juice (use together). |
| Berry Sweet Cupcake | Stronger Mood repair. |
| Yummy Cat Food | Instant-use Mood boost. Consumed on purchase. |

### Stat Consumables
These add permanent points to a specific stat. All are instant-use — consumed
on the turn they are bought.

| Item | Stat Gained |
|---|---|
| Speed Notepad / Stamina Notepad / Power Notepad / Guts Notepad / Wit Notepad | +small points to named stat |
| Speed Manual / Stamina Manual / Power Manual / Guts Manual / Wit Manual | +medium points to named stat |
| Speed Scroll / Stamina Scroll / Power Scroll / Guts Scroll / Wit Scroll | +large points to named stat |
| Grilled Carrots | Instant-use, adds to a stat and bond. |

### Race-Use Items (Hammers and Glow Sticks)
These are used immediately before or during races to boost performance.

| Item | Use Case |
|---|---|
| Master Cleat Hammer | Used before Grade 1 and Climax races for a large performance boost. The most valuable pre-race item. |
| Artisan Cleat Hammer | Fallback when no Master Cleat Hammer is available. Used before Grade 2 races or when Master Cleat Hammers are reserved. |
| Glow Sticks | Used before high-fan-value races when the fan count is above the minimum threshold. |

### Training Amplifiers
These boost training results when used on a training turn.

| Item | Effect |
|---|---|
| Motivating Megaphone | Large training bonus. Best used during bootcamp. |
| Empowering Megaphone | Large training bonus. Best used during bootcamp. |
| Coaching Megaphone | Training bonus, but affects a different part of the formula. |
| Speed Ankle Weights / Stamina Ankle Weights / Power Ankle Weights / Guts Ankle Weights | Held item. Adds a bonus to the matching stat on each training turn until consumed. |
| Reset Whistle | Rerolls the current training selection when the best available training is poor. |
| Good-Luck Charm | Reduces the penalty for failed training attempts. Used before uncertain turns. |

### One-Time Permanent Buffs
These are instant-use items that apply a permanent bonus and are never wasted.

| Item | Effect |
|---|---|
| Pretty Mirror | Instant permanent bonus. |
| Reporter's Binoculars | Instant permanent bonus. |
| Master Practice Guide | Instant permanent bonus. |
| Scholar's Hat | Instant permanent bonus. |

### Ailment Cures
Each ailment has exactly one cure item. If the trainee does not have that
ailment, the item is useless to buy.

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

The bot's shop logic runs one turn at a time. It scores each available item and
decides whether to buy it based on the current game state. It cannot look
backwards and say: "In the last 15 careers, every time `climax_master_hammer_reserve`
was set to 3 but fewer than 3 Climax races ran, the waste flag fired — the reserve
should be 2."

That backward-looking pattern recognition requires memory across careers. Storing
it as text and asking a language model to interpret it each time is unreliable —
LLMs can hallucinate, drift, and cannot be tested deterministically. Instead, this
system stores every career as a **flat numeric record** and runs a deterministic
optimizer over those records. The optimizer computes which settings values correlate
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
(b) a novel waste flag combination appears with no matching past records to draw
from; or (c) a human explicitly requests an explanation. The LLM produces
human-readable text only. It never writes config values.

The optimizer converges. Given enough careers with no human direction overrides,
it will find the settings range where all waste flags consistently do not fire.
That is the optimal configuration — discovered by data, not designed upfront.

---

## Connecting a Bot to This System

### The Universal Shop Profile (The Common Language)

Different bots store their shop settings under different internal names, in
different formats, with different value ranges. A bot written in Python with
a JSON config file and a bot written in JavaScript with a database schema cannot
directly compare their settings — even if they are solving the same problem.

This system requires every connected bot to translate its internal settings into
a **Universal Shop Profile** before submitting a career record. Think of it like
currency exchange: Japanese yen and Korean won are different currencies, but both
convert to US dollars for international transactions. The Universal Shop Profile
is the dollar — the common format every bot speaks when talking to the optimizer.

When the optimizer outputs an updated settings vector, it outputs it in the
Universal Shop Profile format. Each bot is then responsible for translating those
values back into its own internal config. The optimizer never knows or cares what
internal names a bot uses — it only speaks the universal format.

### Universal Shop Profile Fields

These are the standardized field names and value types every connected bot must
map to. A bot that does not have a direct equivalent for a field should set it
to its functional default and note the absence.

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
| `skill_point_floor` | Integer | Minimum Skill Points required for the force-buy to trigger (prevents buying at 0 Skill Points) |
| `dump_window_start_turn` | Integer | Turn at which the bot enters the dump window and relaxes buying restrictions |
| `late_game_save_items` | Integer 0 or 1 | Whether the bot holds items back during the dump window (1) or spends aggressively (0) |
| `ankle_weights_max_stock` | Integer | Maximum Ankle Weights of one type to hold in inventory at once |

**Critical warning:** If `skill_point_hoard_threshold` and `skill_point_floor`
are both set above realistic mid-career Skill Point levels, neither skill-buying
trigger can fire. This is the single most destructive configuration mistake — it
causes the bot to finish the career with all Skill Points unspent. The optimizer
will detect this pattern when `skill_buy_failure` = 1 co-occurs with both
thresholds above their safe ranges and will adjust them downward.

### How a Bot Connects

1. At the start of each career, the bot translates its internal settings into the
   Universal Shop Profile and records the active values as the settings vector.
2. At the end of each career, the bot writes the completed numeric career record
   to the record database.
3. The optimizer reads the last N non-human-directed records and computes the new
   settings vector. Output is a set of integer values in Universal Shop Profile
   format.
4. The bot translates the new settings vector back to its internal config and
   applies it before the next career starts.

The bot's internal logic does not change. Only the translation layer at the
boundary changes.

---

## The Numeric Career Record

Every career is stored as a flat numeric record. There are no free-text fields
in the analysis path. All values are integers or 0/1 flags.

### Settings Vector

The Universal Shop Profile values active during this career. All integers.
See the field table above.

### Outcomes Vector

| Field | Type | Description |
|---|---|---|
| `item_execution_score` | Integer 0–20 | Computed waste score (see Run Score section) |
| `sp_remaining` | Integer | Skill Points owned at career end |
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

### Waste Flag Vector

All fields are 0 or 1. A flag set to 1 means the waste condition occurred.

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
| `bootcamp_mega_shortage` | Fewer Megaphones available at bootcamp entry than the target |
| `climax_hammer_excess` | More Master Cleat Hammers reserved than Climax races that actually ran |
| `coin_hoard` | More than 50 coins remaining at career end |
| `sp_catchall_blocked` | Both the Skill Point hoard threshold and floor were above realistic mid-career Skill Point levels simultaneously, blocking all skill buying |
| `vita_never_triggered` | Vita items were purchased but the energy threshold was never breached |

### Human Direction Flag

| Field | Type | Description |
|---|---|---|
| `human_directed` | Integer 0 or 1 | Set to 1 if any manual priority rating was non-zero or any value override was active. Records with `human_directed = 1` are excluded from optimizer input. |

### Human Annotation (Optional)

A free-text notes field may be attached to a record by a human after the career
ends. It is not read by the optimizer. It exists solely so a human reviewing the
LLM's exception output can attach context for their own reference.

---

## How the Optimizer Works

The optimizer runs after every career in which `human_directed = 0`. It requires
at least 3 eligible records before making any adjustment; with fewer records it
outputs the current settings unchanged.

### Step 1: Compute flag rates per settings value

For each waste flag and each settings field, the optimizer groups past records by
the settings field's value and computes the rate at which that flag fires. A
setting value that predicts a high flag rate is misconfigured.

**Example — `climax_master_hammer_reserve` vs `climax_hammer_excess`:**

| `climax_master_hammer_reserve` value | `climax_hammer_excess` flag rate (last 6 careers) |
|---|---|
| 3 | 4 out of 4 careers (100%) |
| 2 | 0 out of 2 careers (0%) |

The optimizer reads: value 3 → flag fires 100% of the time. Value 2 → flag never
fires. Adjustment direction: decrease toward 2.

**Example — `skill_point_hoard_threshold` vs `skill_buy_failure`:**

| `skill_point_hoard_threshold` | `skill_point_floor` | `skill_buy_failure` flag rate |
|---|---|---|
| ≥ 1400 | ≥ 1000 | 3 out of 3 careers (100%) |
| ≤ 1000 | ≤ 500 | 0 out of 3 careers (0%) |

The optimizer reads: both thresholds above mid-career Skill Point levels → flag
fires every time. Adjustment: reduce both thresholds.

**Example — `energy_buy_threshold` vs `vita_waste` and `vita_never_triggered`:**

| `energy_buy_threshold` | `vita_waste` flag rate |
|---|---|
| below 35 | 3 out of 4 careers (75%) |
| 35–50 | 0 out of 4 careers (0%) |

The optimizer reads: threshold too low → energy items bought but never triggered.
Adjustment: raise threshold toward the clean-career mean.

### Step 2: Compute adjustment

For each settings field where a misconfigured value is detected:

```
clean_mean   = mean value of that field across careers where all waste flags = 0
current      = current active value of that field
step         = (clean_mean - current) × 0.15   [max 15% move per cycle]
new_value    = round(current + step)
```

The 15% step limit prevents a single bad outlier career from causing a large
overcorrection. The system moves toward the clean-career mean incrementally each
cycle.

### Step 3: Output

The optimizer outputs a complete settings vector with all field values as integers.
Fields that had no misconfiguration detected are unchanged from the current values.
This vector is applied directly to the bot's config before the next career.

No text. No explanation. Just numbers.

---

## Manual Direction Input

The human operator can submit numerical overrides before or during a career to
pin specific settings or shift the optimizer's starting point. These are numbers
only — the optimizer reads them directly without interpretation.

### The Rating Scale

Priority ratings adjust the optimizer's scoring weight for a dimension. They are
applied as multipliers on the adjustment step, not as absolute overrides.

| Rating | Effect on optimizer step for that dimension |
|---|---|
| +2 | Step size × 2.0 (move twice as fast toward optimal) |
| +1 | Step size × 1.5 |
|  0 | Default step size (no modification) |
| -1 | Step size × 0.5 (move half as fast) |
| -2 | Step size × 0 (freeze this dimension — optimizer makes no adjustment) |

### Priority Ratings (What to Emphasize)

| Dimension | What it controls |
|---|---|
| `energy_priority` | Optimizer adjustment speed for `energy_buy_threshold` |
| `mood_priority` | Optimizer adjustment speed for mood-related thresholds |
| `bootcamp_mega_priority` | Optimizer adjustment speed for `bootcamp_strong_mega_target` |
| `hammer_conservation` | Optimizer adjustment speed for `climax_master_hammer_reserve` |
| `skill_spending_urgency` | Optimizer adjustment speed for skill-point thresholds and force turn |
| `dump_aggression` | Optimizer adjustment speed for `dump_window_start_turn` and `late_game_save_items` |
| `ankle_weights_priority` | Optimizer adjustment speed for `ankle_weights_max_stock` |
| `coaching_mega_priority` | Optimizer adjustment speed for `coaching_mega_enabled` |

**Example priority rating input:**
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

This tells the optimizer: move energy threshold slowly this cycle, move mood
thresholds quickly, freeze coaching mega (do not adjust it at all).

### Value Overrides (Exact Numbers)

These pin a specific Universal Shop Profile field to an exact value for the next
career, bypassing the optimizer's output for that field. The career that runs with
a value override is marked `human_directed = 1` and excluded from the optimizer's
input pool.

| Override Field | Example | Effect |
|---|---|---|
| `climax_master_hammer_reserve` | `= 2` | Hold exactly 2 Master Cleat Hammers for Climax |
| `climax_artisan_hammer_reserve` | `= 1` | Hold exactly 1 Artisan Cleat Hammer as fallback |
| `bootcamp_strong_mega_target` | `= 3` | Hold exactly 3 strong Megaphones going into bootcamp |
| `skill_point_force_turn` | `= 55` | Force Skill Point spending at turn 55 |
| `dump_window_start_turn` | `= 62` | Start the dump window at turn 62 |
| `master_hammer_buy_cap_turn` | `= 60` | Stop buying new Master Cleat Hammers after turn 60 |

Value overrides take precedence over priority ratings. If `climax_master_hammer_reserve = 2`
is set and `hammer_conservation: +2` is also set, the value of 2 is used and the
rating has no additional effect.

### What Overrides Cannot Do

- Override the auto solver's race decisions.
- Override emergency energy use — if the trainee has zero Energy before a
  mandatory race the bot cannot skip, an energy item is used regardless of
  any rating.
- Override running style selection.

---

## The Run Score for Shop Performance

Each career receives a numeric Item Execution score (0–20) stored in the outcomes
vector. This score is the primary signal the optimizer uses to measure whether
settings are improving.

Item Execution is scored as follows:

- Base: items consumed ÷ items purchased, weighted by item coin value
- Master Cleat Hammers and Vita items carry higher weight than Reset Whistles
  or Good-Luck Charms — a wasted 40-coin Master Cleat Hammer is a larger penalty
  than a wasted 20-coin Reset Whistle
- Zero Master Cleat Hammers or Vita items in final inventory = full sub-score
  for those categories
- Each Motivating or Empowering Megaphone in final inventory after turn 65
  applies a heavy deduction

A career that bought 20 items and used all 20 scores higher than one that bought
30 items and used 25. The optimizer treats buying less and using all of it as
strictly better than buying more and wasting some.

**Regression detection:** If the 3-career rolling mean of `item_execution_score`
drops more than 2 points after an optimizer adjustment, the exception handler is
triggered and the LLM is invoked to explain which setting changed and what the
data showed.

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
          Optimizer runs (requires ≥ 3 eligible records)
          For each settings field:
            — compute waste flag rate at current value
            — compute adjustment step toward clean-career mean
            — apply 15% step limit
          Output: new settings vector (integers)
                │
                ▼
          New settings applied before next career
                │
                ▼
          Regression check: 3-career rolling mean of item_execution_score
                │
                ├── Score dropped > 2 points from prior mean
                │         → Exception: LLM invoked
                │         → LLM identifies which setting changed and what
                │           the optimizer saw in the records
                │         → Human can apply a value override to correct it
                │           or accept the adjustment and wait for more data
                │
                └── Score stable or improved
                          → No action. Loop continues.
```

Human involvement is only triggered by regressions or novel flag combinations.
The optimizer runs silently every career otherwise.

---

## Exportable Learnings (Community Knowledge Packs)

### The Problem With Starting From Zero

A new user who just connected their bot to this system has an empty record
database. The optimizer has no past records to run on — it will output the current
settings unchanged until 3 eligible careers are completed. During those first
careers the bot runs blind, potentially repeating mistakes the community already
solved.

### What a Knowledge Pack Is

A Knowledge Pack is a pre-seeded safe-range table derived from the community's
accumulated career records, stripped of any personal career data. It contains no
raw records — only the numeric safe ranges that the optimizer can use as a
starting point before local records exist.

A Knowledge Pack contains two things:

**1. Safe Starting Ranges**
For each Universal Shop Profile field, the value range that has produced
`item_execution_score` above 15 across confirmed non-human-directed careers
from contributing users.

Example:
```json
{
  "energy_buy_threshold":        { "min": 35, "max": 50 },
  "climax_master_hammer_reserve": { "min": 2,  "max": 3  },
  "bootcamp_strong_mega_target":  { "min": 2,  "max": 3  },
  "skill_point_hoard_threshold":  { "min": 800,"max": 1200},
  "skill_point_force_turn":       { "min": 55, "max": 65 }
}
```

**2. Known Failure Conditions**
Settings combinations that have produced a specific waste flag in 3 or more
independent careers. Stored as numeric threshold conditions, not text.

Example:
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

---

## Constraints on the LLM Layer

The LLM is a secondary tool. These constraints define its role precisely.

- **The LLM never writes configuration values.** The optimizer is the sole source
  of config updates. LLM output is text for human consumption only.
- **The LLM is not consulted on routine careers.** It is only invoked on
  regression detection or novel flag combinations. Running it every career is
  wasteful and introduces interpretation variability where determinism is available.
- **The LLM does not override the optimizer.** If the LLM and optimizer disagree,
  the human resolves it by applying a value override. The override marks the career
  `human_directed = 1` and excludes it from the optimizer's input pool.
- **The LLM never promotes a human-directed run as evidence of optimal settings.**
  A run where a human forced specific behavior is an experiment. It is excluded
  from the optimizer's input and cannot update the safe ranges.
- **Failure records are never cleared.** Past records where waste flags fired are
  the most valuable records in the database — they are what the optimizer uses to
  identify which settings values cause waste.
- **The LLM never conflates instant-use items with held items when measuring waste.**
  Instant-use items (Notepads, Manuals, Scrolls, Grilled Carrots, and others)
  cannot be wasted — they are consumed the moment they are purchased. Waste
  analysis only applies to held items that sit in inventory.
