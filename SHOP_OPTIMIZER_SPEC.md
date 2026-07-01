# SHOP_OPTIMIZER_SPEC.md — Self-Tuning Shop Policy Optimizer

A bot-agnostic shop optimization system with three components: live shop
policies, a deterministic post-career learning optimizer, and an exception-only
LLM explanation layer. All **automated** configuration changes are driven by a
**deterministic numeric optimizer** that reads past career records and updates
settings automatically. Human overrides may pin values explicitly, but those runs
are marked `human_directed` and excluded from optimizer learning. A language model
(LLM) is a tertiary layer — invoked only for exception handling and human-readable
explanation, never for configuration decisions.

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
| Shop Policy Mode | Which shop decision policy is currently active: `native`, `deterministic`, `native_with_deterministic_shadow`, `hybrid`, or `manual`. The active mode determines which policy makes live shop decisions, but all modes must emit canonical telemetry. |
| Native Shop Policy | The bot's original built-in shop decision logic, implemented independently of this spec. Makes live buy/use/skip decisions when `shop_optimizer_mode = "native"` or `"native_with_deterministic_shadow"`. |
| Deterministic Shop Policy | The live shop decision engine defined by this spec. Reads the Universal Shop Profile and applies learned settings to make buy/use/skip decisions. Active when `shop_optimizer_mode = "deterministic"`. This is a live decision component — it does not read career records or update settings. |
| Shop Learning Optimizer | The post-career component that reads completed career records and computes an updated settings vector. Separate from the live decision policy. Runs after every career regardless of which policy made the live decisions. |
| Adapter Layer | The bot-specific translation code that converts internal settings to Universal Shop Profile fields and back. The optimizer never touches bot-internal names or structures. |
| Policy Router | The component that reads `shop_optimizer_mode` and dispatches a turn's shop decision to the correct policy, then routes the result through the shared telemetry layer. |
| Interop Manifest | A machine-readable declaration of which Universal Shop Profile fields a bot implementation supports, which policy modes it implements, and which spec versions it conforms to. |
| Conformance Fixture | A frozen test case: a specific optimizer input paired with a canonical expected output. Used to prove that two bot implementations apply the optimizer algorithm identically. |
| Conformance Hash | A deterministic hash of the canonical optimizer output. Two bots that produce the same hash from the same input apply the same algorithm. |
| Evidence Type | A label on a Knowledge Pack declaring whether its contributing records came from deterministic-policy runs, native-policy runs, or a mix. Determines how much trust an importing bot should assign. |
| Universal Profile Source | A per-career field recording how the career's Universal Shop Profile snapshot was produced: directly applied, derived from native logic, partially mapped, defaulted, or unknown. |
| Record Eligibility | A per-career field that classifies how much an individual career record may contribute to learning. `direct_learning` records (deterministic policy, profile directly applied) may update clean-career means. `observational_learning` records (native policy, derived profile) contribute only to waste pattern detection. See Record Eligibility Rules section. |
| Expert Seed Defaults | Hardcoded bootstrap values derived from expert gameplay analysis. They provide safer initial settings before local `direct_learning` records or accepted deterministic Knowledge Packs exist. They are not optimizer-learned data, not clean-career evidence, and not Knowledge Pack evidence. Lower trust than accepted deterministic Knowledge Packs and local `direct_learning` records. See Expert Seed Defaults section. |
| Shadow Mode | A policy mode (`native_with_deterministic_shadow`) in which native policy makes the live decision and the deterministic shop policy runs silently in parallel on the same context, logging what it would have decided without executing it. |
| Canonical Item ID | A snake_case identifier for each in-game item, stable across bot implementations, languages, and display name changes (e.g. `vita_40`, `master_cleat_hammer`). Used in all cross-bot telemetry and Knowledge Packs. |

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

All items are referenced in telemetry and Knowledge Packs by their **canonical
item ID** — a stable snake_case identifier. Display names are for human reading
only. Canonical IDs are defined in `reference/canonical_items.json` (see
Recommended Repository Structure section). That file is the authoritative source
for IDs, display names, categories, costs, held/instant-use status, and waste
eligibility for each item.

### Energy and Vitality Items

Energy items are divided into two categories with different waste eligibility:

**Held energy items** (go into inventory; can become waste):

| Canonical ID | Display Name | Energy Restored | Cost |
|---|---|---|---|
| `vita_20` | Vita 20 | 20 | 35 coins |
| `vita_40` | Vita 40 | 40 | 55 coins |
| `vita_65` | Vita 65 | 65 | 75 coins |
| `royal_kale_juice` | Royal Kale Juice | Full recovery | 70 coins |

**Instant-use energy items** (consumed on purchase; can never be wasted):

| Canonical ID | Display Name | Energy Restored | Cost |
|---|---|---|---|
| `energy_drink_max` | Energy Drink MAX | 5 (emergency only) | 30 coins |
| `energy_drink_max_ex` | Energy Drink MAX EX | Full recovery | 50 coins |

Only held energy items contribute to `vita_waste` or `held_energy_waste_penalty`.
`energy_drink_max` and `energy_drink_max_ex` are instant-use and must never be
penalized as waste, even though they appear in the same in-game category.

### Mood Items

| Canonical ID | Display Name | Effect |
|---|---|---|
| `plain_cupcake` | Plain Cupcake | Repairs bad Mood. Synergizes with Royal Kale Juice (use together). |
| `berry_sweet_cupcake` | Berry Sweet Cupcake | Stronger Mood repair. |
| `yummy_cat_food` | Yummy Cat Food | Instant-use Mood boost. Consumed on purchase. |

### Stat Consumables (all instant-use)

| Canonical ID Pattern | Display Name | Stat Gained |
|---|---|---|
| `{stat}_notepad` | Speed/Stamina/Power/Guts/Wit Notepad | +small points to named stat |
| `{stat}_manual` | Speed/Stamina/Power/Guts/Wit Manual | +medium points to named stat |
| `{stat}_scroll` | Speed/Stamina/Power/Guts/Wit Scroll | +large points to named stat |
| `grilled_carrots` | Grilled Carrots | Instant-use, adds to a stat and bond. |

### Race-Use Items (Hammers and Glow Sticks)

| Canonical ID | Display Name | Use Case |
|---|---|---|
| `master_cleat_hammer` | Master Cleat Hammer | Used before Grade 1 and Climax races for a large performance boost. The most valuable pre-race item. |
| `artisan_cleat_hammer` | Artisan Cleat Hammer | Fallback when no Master Cleat Hammer is available. Used before Grade 2 races. |
| `glow_sticks` | Glow Sticks | Used before high-fan-value races when the fan count is above the minimum threshold. |

### Training Amplifiers

| Canonical ID | Display Name | Effect |
|---|---|---|
| `motivating_megaphone` | Motivating Megaphone | Large training bonus. Best used during bootcamp. |
| `empowering_megaphone` | Empowering Megaphone | Large training bonus. Best used during bootcamp. |
| `coaching_megaphone` | Coaching Megaphone | Training bonus, but affects a different part of the formula. |
| `ankle_weights_{stat}` | Speed/Stamina/Power/Guts Ankle Weights | Held item. Adds a bonus to the matching stat on each training turn until consumed. |
| `reset_whistle` | Reset Whistle | Rerolls the current training selection when the best available training is poor. |
| `good_luck_charm` | Good-Luck Charm | Reduces the penalty for failed training attempts. Used before uncertain turns. |

### One-Time Permanent Buffs (all instant-use)

| Canonical ID | Display Name |
|---|---|
| `pretty_mirror` | Pretty Mirror |
| `reporters_binoculars` | Reporter's Binoculars |
| `master_practice_guide` | Master Practice Guide |
| `scholars_hat` | Scholar's Hat |

Each applies an immediate permanent bonus. Never wasted.

### Ailment Cures

| Ailment | Canonical Item ID | Display Name |
|---|---|---|
| Night Owl | `fluffy_pillow` | Fluffy Pillow |
| Slacker | `pocket_planner` | Pocket Planner |
| Skin Outbreak | `rich_hand_cream` | Rich Hand Cream |
| Slow Metabolism | `smart_scale` | Smart Scale |
| Migraine | `aroma_diffuser` | Aroma Diffuser |
| Practice Poor | `practice_drills_dvd` | Practice Drills DVD |
| Any ailment | `miracle_cure` | Miracle Cure |

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

### Three Components

**Component 1 — The Shop Policy Router and Live Policies:**
Decides what the bot does on each turn. The `shop_policy_router` dispatches to
the configured policy (`native_shop_policy`, `deterministic_shop_policy`, or a
shadow combination). The `deterministic_shop_policy` reads the current Universal
Shop Profile values and applies their learned settings to make live buy/use/skip
decisions. It does not read career records — it only consumes the settings vector
produced by the learning optimizer.

**Component 2 — The Shop Learning Optimizer (primary, automated):**
A deterministic function that runs after every career. Reads the numeric career
record database. Computes correlations between settings values and waste flag
outcomes. Outputs a new Universal Shop Profile settings vector. No human input
required. No text. No interpretation. Feeds its output to the deterministic shop
policy before the next career.

The shop learning optimizer gradually moves settings toward lower-waste ranges
observed in prior careers. It is expected to improve shop behavior over repeated
runs, but it does not prove global optimality. It cannot evaluate whether the bot
is buying the *best* items or simply *fewer* items.

**Component 3 — The LLM Exception Layer (tertiary, exception-triggered):**
A language model. Only invoked when: (a) the learning optimizer produces a
regression — Item Execution score drops more than 2 points below the prior
3-career mean; (b) a novel waste flag combination appears with no matching past
records; or (c) a human explicitly requests an explanation. The LLM produces
human-readable text only. It never writes config values.

---

## Bot-Agnostic Design Principles

Different bots have different internal shop implementations, config formats,
execution loops, and frontends. This system must be safe to adopt without requiring
a bot to replace or discard its existing shop logic.

The design separates two responsibilities that must never be merged in any
implementation.

### Responsibility 1 — Shop Decision Policy

This is the component that decides what the bot actually does on each turn:
which item to buy, which item to use, and when to skip the shop.

Allowed policy modes:

| Mode | Meaning |
|---|---|
| `native` | The bot's original built-in shop logic. |
| `deterministic` | The deterministic shop policy defined by this spec. |
| `native_with_deterministic_shadow` | Native policy executes live; deterministic shop policy runs silently in parallel and logs its hypothetical decision. Optional but recommended for adoption. |
| `hybrid` | A custom combination of native and deterministic policies. |
| `manual` | Human-directed mode; no policy automation active. |

Only `native` and `deterministic` are mandatory. A bot may omit
`native_with_deterministic_shadow`, `hybrid`, and `manual`.

### Responsibility 2 — Shop Learning Optimizer and Telemetry Layer

This is the component that records what happened during a career using the shared
schema, and then updates the settings vector after the career. It must run
regardless of which shop decision policy was active.

The telemetry and learning layer is always mandatory. It includes:

- Universal Shop Profile snapshot export
- Numeric career record export (including `record_eligibility` classification)
- Waste flag computation
- Item Execution score computation
- Turn-level shop log export
- Policy mode metadata recording
- Shop learning optimizer (post-career settings update)
- Knowledge Pack export

The decision policy may vary between bots and between careers.
**The telemetry contract must not vary.**

### The Separation Mandate

The `deterministic_shop_policy` and the `shop_learning_optimizer` must each be
implemented as **separate modules** from the bot's native shop logic. A coding
agent applying this spec to a bot repository must not overwrite or entangle the
bot's existing native shop code.

**Incorrect implementation (do not do this):**

```
existing_shop_logic.py
  └── native logic modified until it becomes the deterministic shop policy
```

**Correct implementation:**

```
shop/
  native_shop_policy.py               ← untouched native logic
  deterministic_shop_policy.py        ← new live decision policy
  shop_learning_optimizer.py          ← post-career settings updater
  shop_policy_router.py               ← reads shop_optimizer_mode, dispatches
  optimizer_telemetry.py              ← records outcomes regardless of policy
  universal_shop_profile_adapter.py   ← translates internal ↔ Universal fields
```

The bot's native shop logic must remain independently usable after the
deterministic components are added.

**Hard rule for coding agents:**

> Coding agents must not refactor, rewrite, tune, or otherwise modify the native
> shop policy unless the implementation requires a thin telemetry instrumentation
> hook. Native policy behavior must remain unchanged except for that instrumentation.
> Any other change to native policy code — even an apparent improvement — is
> prohibited because it would corrupt the native vs. deterministic comparison data.

If a telemetry hook cannot be added without touching native logic, the agent must
document the minimum required change in a code comment, limit the change to the
smallest possible surface area, and record the modification in the bot's adapter
documentation so future audits can account for it.

### The Telemetry Mandate

> Using the deterministic shop policy is optional.
> Emitting deterministic-compatible telemetry is mandatory.

A bot that uses its native policy for every career still contributes useful
knowledge to the ecosystem, provided it emits canonical records. Native-policy
records can reveal recurring waste patterns, bad timing decisions, and item
failure conditions — the shop learning optimizer can learn from observed outcomes
even when the deterministic shop policy was not the one making decisions.

For `observational_learning` records, "learn" means waste flag rate detection,
timing diagnostics, and native-derived Knowledge Pack evidence only. Observational
records must not update clean-career means, direct safe ranges, or deterministic
setting baselines. Those are reserved exclusively for `direct_learning` records.

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
| `mood_item_buy_enabled` | Integer 0 or 1 | Whether the deterministic shop policy is allowed to buy mood-repair items |
| `mood_item_min_stock` | Integer | Minimum number of mood-repair items the shop policy tries to maintain when racing heavily |
| `mood_item_max_stock` | Integer | Maximum number of mood-repair items to hold before treating additional purchases as low priority |
| `race_chain_mood_break_after` | Integer | Race-chain length after which mood-repair inventory becomes more valuable. Does not force race selection. |
| `cupcake_aggression` | Integer 0–3 | How aggressively the shop policy buys and preserves cupcakes. Higher means more willingness to buy/hold mood items. |
| `rest_avoidance_enabled` | Integer 0 or 1 | Whether the shop policy should value energy and mood items more because the bot prefers avoiding rest. Does not prohibit the race/training solver from resting. |

**Scope rule for mood fields:** These fields must not override the race solver. They only influence how the shop policy buys, reserves, and uses mood-repair items when the race solver is already producing race chains.

**Validation rule:** `mood_item_min_stock` must be ≤ `mood_item_max_stock`. If violated, clamp by setting `mood_item_min_stock = mood_item_max_stock` and log the clamp.

**Critical warning:** If `skill_point_hoard_threshold` and `skill_point_floor` are
both set above realistic mid-career Skill Point levels, neither skill-buying trigger
can fire. This causes the bot to finish with all Skill Points unspent. The optimizer
detects this when `skill_buy_failure = 1` co-occurs with both thresholds above their
safe ranges and adjusts them downward.

### How a Bot Connects

1. At career start, the bot translates its internal settings into the Universal Shop
   Profile and records the active values as the settings vector.
2. At career end, the bot writes the completed numeric career record to the database.
3. The shop learning optimizer reads the last N records according to
   `record_eligibility`: `direct_learning` records may drive full learning,
   `observational_learning` records may contribute to waste flag rates, and
   manual/diagnostic/invalid records are excluded from settings influence.
4. The bot translates the new settings vector back to its internal config before
   the next career starts.

### Required Adapter Layer

Each bot must implement an optimizer adapter that isolates all bot-specific
translation. The optimizer and telemetry layer interact only with the adapter —
never with bot-internal field names, class structures, file paths, or database
layouts.

Required adapter functions:

```
export_universal_shop_profile()                          → Universal Shop Profile dict
import_universal_shop_profile(profile)                   → applies profile to internal config
export_career_record(career_id)                          → career record dict
export_turn_shop_log(career_id)                          → list of turn log dicts
import_knowledge_pack(pack)                              → applies pack as baseline
export_knowledge_pack()                                  → Knowledge Pack dict
run_shop_learning_optimizer(records, profile, pack, dir) → new profile dict
run_conformance_tests(fixtures)                          → list of pass/fail results
```

Required adapter functions for policy routing:

```
get_active_shop_policy()                  → current shop_optimizer_mode string
set_active_shop_policy(mode)              → updates shop_optimizer_mode
run_native_shop_policy(context)           → native policy decision
run_deterministic_shop_policy(context)    → deterministic policy decision (live)
run_shop_learning_optimizer(records, profile, pack, direction) → new profile
emit_optimizer_telemetry(context, decision, policy_mode)       → writes turn log
```

Example field name translation:

| Bot A internal field | Bot B internal field | Universal Shop Profile field |
|---|---|---|
| `climaxHammerReserve` | `shop.items.masterHammer.keepForFinals` | `climax_master_hammer_reserve` |

The optimizer sees only the Universal Shop Profile form. Internal names are the
adapter's private concern.

### Shop Policy Mode and Frontend Toggle

The bot must expose a setting that allows the user to choose which shop decision
policy is active. At minimum, the frontend or config must support `native` and
`deterministic`. `native_with_deterministic_shadow` is strongly recommended.

Recommended UI:

```
Shop Optimizer
[ Native Bot Optimizer ▼ ]

Options:
  Native Bot Optimizer
  Deterministic Shop Policy
  Native + Deterministic Shadow (recommended for testing)
```

Config representation:

```json
{
  "shop_optimizer_mode": "native"
}
```

Allowed values: `native`, `deterministic`, `native_with_deterministic_shadow`,
`hybrid`, `manual`. Only `native` and `deterministic` are mandatory.

The UI should make the data contract clear to the user:

> **Native Bot Optimizer:** Uses this bot's original shop decision logic.
>
> **Deterministic Shop Policy:** Uses the shared SHOP_OPTIMIZER_SPEC live decision
> policy and learned settings from past careers.
>
> **Native + Deterministic Shadow:** Native policy makes live decisions.
> Deterministic policy runs silently in parallel and logs what it would have done.
> Safe for testing — no deterministic decisions are executed.
>
> Regardless of the selected mode, all runs still produce optimizer-compatible
> telemetry and can contribute to Knowledge Pack generation.

### Policy Router Pattern

The policy router reads `shop_optimizer_mode` at the start of each turn's shop
decision and dispatches to the correct policy. The telemetry layer runs after the
decision, regardless of which policy was used.

The full system flow, from live decisions through post-career learning:

```
native_shop_policy ───────────────┐
                                  ├── shop_policy_router ─── live decision
deterministic_shop_policy ────────┘
                                             │
                                             ▼
                                  canonical telemetry layer
                                             │
                                             ▼
                                  shop_learning_optimizer
                                             │
                                             ▼
                                  Knowledge Packs
```

Turn-by-turn router flow:

```
Turn begins
      │
      ▼
Build shop decision context
      │
      ▼
Read shop_optimizer_mode
      │
      ├── native → run native_shop_policy(context)
      │            record active_policy_decision in turn log
      │
      ├── deterministic → run deterministic_shop_policy(context)
      │                   record active_policy_decision in turn log
      │
      ├── native_with_deterministic_shadow →
      │            run native_shop_policy(context)       ← executes live
      │            run deterministic_shop_policy(context) ← runs silently
      │            record active_policy_decision (native result)
      │            record shadow_policy_decision (deterministic result)
      │            record shadow_decision_executed = 0
      │
      └── hybrid → run configured hybrid policy
      │
      ▼
Execute selected shop decision
      │
      ▼
emit_optimizer_telemetry(context, decision, policy_mode)
      │
      ▼
At career end: shop_learning_optimizer runs, emits canonical career record
```

The telemetry layer records what state existed, what items were offered, what
decision was made (and what the shadow policy would have done), and what happened
by career end. It does not care which policy made the executed decision.

**Important:** Native runs contribute telemetry to the `shop_learning_optimizer`,
even when the `deterministic_shop_policy` was not active. The learning optimizer
is always the consumer of career records — the live policy is separate from it.

### Interop Manifest

Every bot implementing the optimizer must expose a machine-readable interop
manifest. This manifest tells other bots what the implementation supports and which
spec versions it conforms to.

```json
{
  "shop_optimizer_schema_version": "1.0.0",
  "optimizer_algorithm_version": "1.0.0",
  "scoring_version": "1.0.0",
  "record_eligibility_version": "1.0.0",
  "ruleset": "umamusume_make_a_new_track",
  "bot_name": "example-bot",
  "bot_optimizer_adapter_version": "0.3.0",
  "item_name_mapping_version": "1.0.0",
  "supports_native_policy": true,
  "supports_deterministic_shop_policy": true,
  "supports_shop_learning_optimizer": true,
  "supports_shadow_mode": true,
  "supports_policy_toggle": true,
  "emits_telemetry_for_native_policy": true,
  "supported_policy_modes": ["native", "deterministic", "native_with_deterministic_shadow"],
  "supported_fields": [
    "energy_buy_threshold",
    "climax_master_hammer_reserve",
    "climax_artisan_hammer_reserve",
    "master_hammer_buy_cap_turn",
    "glow_sticks_min_fans",
    "bootcamp_strong_mega_target",
    "coaching_mega_enabled",
    "skill_point_buy_threshold",
    "skill_point_hoard_threshold",
    "skill_point_force_turn",
    "skill_point_floor",
    "dump_window_start_turn",
    "late_game_save_items",
    "ankle_weights_max_stock",
    "mood_item_buy_enabled",
    "mood_item_min_stock",
    "mood_item_max_stock",
    "race_chain_mood_break_after",
    "cupcake_aggression",
    "rest_avoidance_enabled"
  ],
  "unsupported_fields": [],
  "passes_conformance_suite": true
}
```

If a bot does not support a Universal Shop Profile field directly, it must declare
that field under `unsupported_fields` and provide the functional default it uses
instead. Unsupported fields must never be silently hidden — they must be declared.

---

## The Numeric Career Record

Every career is stored as a flat numeric record. No free-text fields in the analysis
path. All values are integers or 0/1 flags.

### Settings Vector

The Universal Shop Profile values active during this career. All integers.

### Policy Mode Metadata

These fields record how the career's shop decisions were made and how the Universal
Shop Profile snapshot was produced. They are stored alongside the settings vector
and outcomes vector.

| Field | Type | Description |
|---|---|---|
| `shop_policy_mode` | String | Active policy: `"native"`, `"deterministic"`, `"native_with_deterministic_shadow"`, `"hybrid"`, or `"manual"` |
| `shop_policy_id` | String | Internal identifier for the specific optimizer implementation |
| `shop_policy_version` | String | Version string of the active policy implementation |
| `universal_profile_source` | String | How the Universal Shop Profile snapshot was produced (see table below) |
| `deterministic_shop_policy_active` | Integer 0 or 1 | 1 if the deterministic shop policy made live shop decisions; 0 otherwise. The shop learning optimizer runs after every career regardless of this value. |

**`universal_profile_source` values:**

| Value | Meaning |
|---|---|
| `applied_directly` | The Universal Shop Profile directly controlled the active deterministic optimizer. |
| `derived_from_native` | The bot used native logic, but the adapter mapped native behavior into Universal Shop Profile fields. |
| `partially_mapped` | Some Universal fields were mapped; others used functional defaults. |
| `defaulted` | The bot could not map native settings and used safe defaults for the profile snapshot. |
| `unknown` | Mapping quality is unknown. Should not be used for high-trust learning. |

Records with `universal_profile_source` of `defaulted` or `unknown` contribute
to observable waste pattern knowledge but should not be used as clean-career
baselines for optimizer adjustment steps.

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
| `vita_waste` | Any held energy item in final inventory: `vita_20`, `vita_40`, `vita_65`, or `royal_kale_juice` |
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
| `vita_never_triggered` | Held energy items were purchased but the energy threshold was never breached |

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

**Mood Diagnostic Flags** (optional; start as diagnostic only — do not score as core penalties until telemetry is sufficient to avoid false positives)

| Flag | Set to 1 when |
|---|---|
| `mood_item_shortage` | Mood dropped to Bad or Awful during a race chain and no mood item was available |
| `mood_item_overstock` | More than `mood_item_max_stock` mood items remained in inventory after turn 65 |
| `cupcake_unused_late` | A Plain Cupcake or Berry Sweet Cupcake remained unused in final inventory |
| `race_chain_mood_break_failed` | Race chain exceeded `race_chain_mood_break_after`, mood fell below Normal, and no mood repair occurred |
| `rest_avoidance_item_gap` | Rest was taken while no energy or mood item was available that could have plausibly prevented the rest |

### Record Eligibility

| Field | Type | Description |
|---|---|---|
| `record_eligibility` | String | Classification of how much this record may contribute to learning. See Record Eligibility Rules section. |
| `record_eligibility_version` | String | Version of the eligibility computation rules used to produce this value (e.g. `"1.0.0"`). Required for future auditability if eligibility rules change. |

The `record_eligibility` field is computed from `shop_policy_mode`,
`universal_profile_source`, and `human_directed` at career end. It is a single
derived field that replaces the need to re-check multiple fields at query time.
The `record_eligibility_version` must match the version declared in the Interop
Manifest and Knowledge Pack — a version mismatch means old records may have been
classified under different rules and should be treated as `diagnostic_only`.

| Value | Meaning | Allowed Use |
|---|---|---|
| `direct_learning` | Deterministic policy active; Universal Profile directly applied | Full learning: clean-career means, safe ranges, waste flag rates, Knowledge Packs |
| `observational_learning` | Native policy active; profile derived from native behavior | Waste pattern detection, timing diagnostics, lower-trust ranges, native-derived Knowledge Packs |
| `diagnostic_only` | Partial/default/unknown profile mapping | Human review, LLM explanation, aggregate diagnostics only — no optimizer influence |
| `excluded_manual` | Human-directed run | Store for history; excluded from all optimizer learning |
| `invalid` | Missing or corrupt telemetry | Ignored by all optimizer and Knowledge Pack export paths |

**Critical rule:** Only `direct_learning` records may update deterministic
clean-career means. See Record Eligibility Rules for the full specification.

### Human Direction Flag

| Field | Type | Description |
|---|---|---|
| `human_directed` | Integer 0 or 1 | Set to 1 if any manual priority rating was non-zero or any value override was active. Records with `human_directed = 1` receive `record_eligibility = "excluded_manual"` and are excluded from optimizer input. |

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

### Action and Mood Context

| Field | Type | Description |
|---|---|---|
| `current_race_chain_length` | Integer | Number of consecutive race actions immediately before or including this turn |
| `races_in_last_5_turns` | Integer | Count of race actions in the last 5 turns |
| `action_taken` | String | `"train"`, `"race"`, `"rest"`, `"recreation"`, `"outing"`, `"shop_only"`, or `"other"` |
| `rest_taken` | Integer 0 or 1 | Whether the bot rested this turn |
| `recreation_taken` | Integer 0 or 1 | Whether the bot used recreation this turn |
| `mood_item_available` | Integer 0 or 1 | Whether a mood-repair item was available in inventory before action resolution |
| `energy_item_available` | Integer 0 or 1 | Whether a held energy item was available in inventory before action resolution |
| `mood_item_used_this_turn` | String or null | Canonical item ID of mood item used this turn, or null |
| `energy_item_used_this_turn` | String or null | Canonical item ID of energy item used this turn, or null |
| `pre_action_mood` | Integer 1–5 | Mood before the selected action resolves |
| `post_action_mood` | Integer 1–5 | Mood after action and item effects resolve |

These fields are required to compute `race_chain_mood_break_failed` and `rest_avoidance_item_gap`
reliably. Without them, implementations cannot distinguish between "no mood item existed" and
"a mood item existed but was not used."

### Inventory at Turn Start

| Field | Type | Description |
|---|---|---|
| `inv_master_hammers` | Integer | Master Cleat Hammers in inventory |
| `inv_artisan_hammers` | Integer | Artisan Cleat Hammers in inventory |
| `inv_held_energy_items` | Integer | Total held energy items in inventory: `vita_20`, `vita_40`, `vita_65`, `royal_kale_juice` |
| `inv_strong_megaphones` | Integer | Motivating + Empowering Megaphones in inventory |
| `inv_coaching_megaphones` | Integer | Coaching Megaphones in inventory |
| `inv_ankle_weights` | Integer | Total Ankle Weights in inventory |
| `inv_glow_sticks` | Integer | Glow Sticks in inventory |
| `inv_mood_items` | Integer | Plain Cupcakes + Berry Sweet Cupcakes in inventory |

### Purchase and Skip Decision

| Field | Type | Description |
|---|---|---|
| `shop_items_offered` | JSON array | Canonical item IDs offered in the shop this turn |
| `item_bought` | String or null | Canonical item ID of item purchased, or null |
| `item_bought_cost` | Integer | Coin cost of purchased item, or 0 |
| `skip_reason` | String or null | Reason code if shop was skipped (see table below) |
| `item_used_this_turn` | String or null | Canonical item ID of held item triggered this turn, or null |
| `item_used_context` | String or null | Context code for why item was used (see table below) |

### Policy Decision Record

A structured object recording the full policy decision for this turn. Required
for cross-bot comparison and LLM exception analysis.

| Field | Type | Description |
|---|---|---|
| `policy_decision.decision_type` | String | `"buy_item"`, `"use_item"`, `"skip_shop"`, or `"no_shop"` |
| `policy_decision.item_id` | String or null | Canonical item ID of the item bought or used, or null |
| `policy_decision.reason_code` | String or null | The skip reason or item use context code that drove this decision |
| `policy_decision.score` | Integer or null | Internal scoring value the policy assigned to this decision, if available. **Local diagnostic data only** — must not be compared across bots, cross-policy, or used in Knowledge Pack conformance unless a fixture explicitly defines the scoring algorithm. Native and deterministic policies may use entirely different scoring scales. |
| `policy_decision.policy_mode` | String | Which policy produced this decision |
| `policy_decision.executed` | Integer 0 or 1 | 1 if this decision was actually executed; 0 if this was a shadow decision |

Example:

```json
{
  "policy_decision": {
    "decision_type": "buy_item",
    "item_id": "vita_40",
    "reason_code": "energy_threshold",
    "score": 82,
    "policy_mode": "native",
    "executed": 1
  }
}
```

### Shadow Decision Fields

Present only when `shop_optimizer_mode = "native_with_deterministic_shadow"`.
Records what the deterministic shop policy would have decided without executing it.

**Hard safety rule — shadow policy must be side-effect free:**

> The shadow deterministic policy must not mutate inventory, config, random state,
> telemetry counters, cooldowns, or any other game state. It must run on a deep copy
> of the decision context and return a hypothetical decision object only. Any
> implementation that allows the shadow policy to write to shared state violates
> the separation mandate and must be rejected in code review.

| Field | Type | Description |
|---|---|---|
| `active_policy_decision` | String | Canonical item ID or decision code from the executed (native) policy |
| `shadow_policy_decision` | String | Canonical item ID or decision code the deterministic shop policy would have chosen |
| `shadow_policy_mode` | String | Always `"deterministic"` in standard shadow mode |
| `shadow_decision_executed` | Integer 0 or 1 | Always 0 — shadow decisions are never executed |

Example (native bought Vita 40, deterministic would have skipped):

```json
{
  "active_policy_decision": "buy_item:vita_40",
  "shadow_policy_decision": "skip_shop:not_needed",
  "shadow_policy_mode": "deterministic",
  "shadow_decision_executed": 0
}
```

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

## How the Shop Learning Optimizer Works

### Tiered Adjustment by Record Count

The optimizer's behavior scales with how many eligible records exist. A small
number of noisy early careers should not drive large corrections.

Two record counts are tracked separately:

- `direct_learning_record_count` — count of records with `record_eligibility = "direct_learning"`
- `flag_rate_record_count` — count of records with `record_eligibility` in `"direct_learning"` or `"observational_learning"`

The step-size tier is driven by `direct_learning_record_count` only. Tier
advancement requires direct evidence because only direct records update clean-career
means. `flag_rate_record_count` is used only in Step 1 (waste flag rate computation)
— observational records broaden flag detection but do not increase adjustment
confidence.

| `direct_learning_record_count` | Behavior |
|---|---|
| 0–2 | Collect only. No adjustment made. Output current settings unchanged. |
| 3–4 | Micro-adjustments. Step size capped at 5% per cycle. |
| 5–9 | Small adjustments. Step size capped at 10% per cycle. |
| 10–19 | Normal adjustments. 15% step limit applies. |
| 20+ | Full confidence. 15% step limit applies. |

### Bootstrap Rule for Missing Direct Records

If `direct_learning_record_count = 0`, the shop learning optimizer cannot compute
clean-career means from local data. It must use the safest available source, in
priority order:

1. Accepted external deterministic Knowledge Pack baselines
   (`evidence_type = "deterministic_policy_evidence"`)
2. Expert Seed Defaults (see Expert Seed Defaults section)
3. Default guardrails (see Step 3)
4. Hardcoded safe defaults

The optimizer **must not** compute clean-career means from `observational_learning`
records when no `direct_learning` records exist. A native-only bot can export
useful native-derived Knowledge Packs, but its deterministic clean-career mean
remains unset until the bot runs at least one career with
`shop_policy_mode = "deterministic"` and `universal_profile_source = "applied_directly"`.

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
too late, OR an unusually low `climax_races_run`. The learning optimizer adjusts
the most directly correlated field. When a regression occurs, the LLM exception
handler can surface multi-field interactions (see LLM Exception Layer section).

**Tie-breaking when multiple fields correlate with the same waste flag:**

When two or more settings fields show correlation with the same waste flag,
choose the field to adjust using this deterministic priority order:

1. Highest absolute flag-rate difference between the high-rate and low-rate
   value groups.
2. Highest sample count in the correlated group (more records = more confidence).
3. Explicit `waste_flag_to_field_priority` order (table below).
4. Lexicographic field name as final fallback (earlier in alphabet wins).

**`waste_flag_to_field_priority` — explicit field order per flag:**

| Waste Flag | Priority Order |
|---|---|
| `climax_hammer_excess` | 1. `climax_master_hammer_reserve` 2. `master_hammer_buy_cap_turn` 3. `climax_artisan_hammer_reserve` |
| `vita_never_triggered` | 1. `energy_buy_threshold` 2. `dump_window_start_turn` |
| `bootcamp_mega_shortage` | 1. `bootcamp_strong_mega_target` 2. `master_hammer_buy_cap_turn` |
| `sp_catchall_blocked` | 1. `skill_point_hoard_threshold` 2. `skill_point_floor` |
| `skill_point_hoard` | 1. `skill_point_force_turn` 2. `skill_point_hoard_threshold` |
| `mood_item_shortage` | 1. `mood_item_min_stock` 2. `cupcake_aggression` 3. `mood_item_buy_enabled` |
| `mood_item_overstock` | 1. `mood_item_max_stock` 2. `cupcake_aggression` |
| `cupcake_unused_late` | 1. `mood_item_max_stock` 2. `cupcake_aggression` 3. `dump_window_start_turn` |
| `race_chain_mood_break_failed` | 1. `race_chain_mood_break_after` 2. `mood_item_min_stock` 3. `cupcake_aggression` |
| `rest_avoidance_item_gap` | 1. `rest_avoidance_enabled` 2. `energy_buy_threshold` 3. `mood_item_min_stock` |

This table is the canonical tie-break order. Two bots applying the same records
must choose the same field to adjust. Without this, bots can diverge on field
selection even when they agree on flag rates and step sizes.

**Example — `skill_point_hoard_threshold` vs `skill_buy_failure`:**

| `skill_point_hoard_threshold` | `skill_point_floor` | `skill_buy_failure` rate |
|---|---|---|
| ≥ 1400 | ≥ 1000 | 3 out of 3 careers (100%) |
| ≤ 1000 | ≤ 500 | 0 out of 3 careers (0%) |

### Step 2: Compute Adjustment

For each settings field where a misconfigured value is detected:

```
qualified_clean = careers where:
    — record_eligibility = "direct_learning"   ← ONLY direct_learning records
    — all waste flags = 0
    — item_execution_score ≥ 15
    — skills_purchased ≥ 1
    — bootcamp_mega_shortage = 0

clean_mean   = mean value of that field across qualified_clean careers
current      = current active value of that field
step_limit   = tier table above (5%, 10%, or 15%)
step         = (clean_mean - current) × step_limit
new_value    = round_half_away_from_zero(current + step)
new_value    = clamp(new_value, guardrail_min, guardrail_max)
```

**`record_eligibility` filter is mandatory.** Only records where the
`deterministic_shop_policy` was active and the Universal Profile was directly
applied may update clean-career means. `observational_learning` records (native
policy, derived profile) may contribute to waste flag rate calculations but must
not pull the settings mean. This prevents native bot behavior from being treated
as causal evidence for Universal Shop Profile settings.

The "clean career" definition also requires adequate item use, not just absence of
waste. A career where the bot bought nothing would show no waste flags but would
not qualify because `skills_purchased = 0`. This prevents the learning optimizer
from drifting toward "buy less" as the solution to all waste.

**Mood Diagnostic Flags and `qualified_clean`:**

Mood Diagnostic Flags (`mood_item_shortage`, `mood_item_overstock`, `cupcake_unused_late`,
`race_chain_mood_break_failed`, `rest_avoidance_item_gap`) do **not** disqualify a career
from `qualified_clean` unless a future scoring or conformance version explicitly promotes
them to core waste flags. Until that promotion occurs, they are recorded but not checked
in the `qualified_clean` filter. Implementations must not treat mood diagnostic flags the
same as `master_cleat_waste = 1` or other core waste flags that do block `qualified_clean`.

**No-qualified-clean-records fallback:**

If `direct_learning_record_count > 0` but `qualified_clean` is empty (all
direct-learning records have a waste flag or low score), the optimizer must not
compute `clean_mean` from unqualified records. It must fall back to the
highest-trust available baseline in this order:

1. Accepted external deterministic Knowledge Pack baseline
   (`evidence_type = "deterministic_policy_evidence"`)
2. Expert Seed Defaults
3. Default Universal Shop Profile values
4. Hardcoded safe defaults

The optimizer may still record flag rates and known failure conditions from the
dirty records. It must not adjust toward a `clean_mean` that does not exist.
This fallback is distinct from the `direct_learning_record_count = 0` bootstrap
rule — it covers the case where data exists but none of it qualifies as clean.

### Deterministic Rounding Rule

All optimizer arithmetic uses **half-away-from-zero** integer rounding. This rule
is part of the interoperability contract — conformance fixtures will fail if a
different rounding convention is used.

```
round_half_away_from_zero(x):
  if x ≥ 0: return floor(x + 0.5)
  else:      return ceil(x - 0.5)

Examples:
  2.4  → 2
  2.5  → 3
  2.6  → 3
  -2.4 → -2
  -2.5 → -3
  -2.6 → -3
```

This differs from Python's built-in `round()` (which uses banker's rounding /
round-half-to-even) and from JavaScript's `Math.round()` (which rounds .5 toward
+Infinity). Any implementation must explicitly implement half-away-from-zero rather
than relying on the host language's default rounding.

All intermediate arithmetic uses full floating-point precision. Rounding to integer
is applied once, at the final `new_value = round_half_away_from_zero(current + step)`
step, not at any intermediate calculation.

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
| `coaching_mega_enabled` | 0 | 1 |
| `skill_point_buy_threshold` | 100 | 800 |
| `skill_point_hoard_threshold` | 600 | 1400 |
| `skill_point_force_turn` | 50 | 70 |
| `skill_point_floor` | 100 | 800 |
| `dump_window_start_turn` | 55 | 68 |
| `late_game_save_items` | 0 | 1 |
| `ankle_weights_max_stock` | 0 | 2 |
| `mood_item_buy_enabled` | 0 | 1 |
| `mood_item_min_stock` | 0 | 2 |
| `mood_item_max_stock` | 0 | 3 |
| `race_chain_mood_break_after` | 3 | 6 |
| `cupcake_aggression` | 0 | 3 |
| `rest_avoidance_enabled` | 0 | 1 |

If the computed new value falls outside the range, it is clamped to the nearest
limit. The clamping event is logged so a human can review it.

After clamping, validate `mood_item_min_stock ≤ mood_item_max_stock`. If violated,
set `mood_item_min_stock = mood_item_max_stock` and log the clamp.

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

### Exact Scoring Formula

```
item_execution_score = clamp(0, 20,
  20
  - hammer_waste_penalty
  - held_energy_waste_penalty
  - megaphone_late_penalty
  - skill_failure_penalty
  - coin_hoard_penalty
  - minor_waste_penalty
)
```

**Penalty definitions:**

| Penalty Component | Condition | Deduction |
|---|---|---|
| `hammer_waste_penalty` | Each Master Cleat Hammer in final inventory | 4 points each |
| `held_energy_waste_penalty` | Each held energy item (`vita_20`, `vita_40`, `vita_65`, `royal_kale_juice`) in final inventory | 2 points each |
| `megaphone_late_penalty` | Each Motivating or Empowering Megaphone in final inventory after turn 65 | 3 points each |
| `skill_failure_penalty` | `skill_buy_failure = 1` (zero skills purchased entire career) | 4 points flat |
| `coin_hoard_penalty` | `coins_remaining > 50` at career end | 1 point flat |
| `minor_waste_penalty` | Each Reset Whistle, Good-Luck Charm, or Artisan Cleat Hammer in final inventory | 1 point each |

All penalties are additive. The total is subtracted from 20 and then clamped to [0, 20].

Instant-use items (Yummy Cat Food, Grilled Carrots, all Stat Notepads/Manuals/Scrolls,
Pretty Mirror, Reporter's Binoculars, Scholar's Hat, Master Practice Guide,
Energy Drink MAX, Energy Drink MAX EX) can never be wasted and never generate any
penalty. Ailment cure waste eligibility is defined by `canonical_items.json`. If a
cure item is marked instant-use there, it cannot be wasted. If marked held, it may
contribute to `minor_waste_penalty` when left in final inventory. Only held items
contribute to waste penalties.

A career that bought 20 items and used all 20 scores higher than one that bought
30 items and used 25. The optimizer treats buying less and using all of it as
strictly better than buying more and wasting some.

**Regression detection:** If the 3-career rolling mean of `item_execution_score`
drops more than 2 points after a learning optimizer adjustment, the LLM exception
handler is triggered.

---

## The Automated Feedback Loop

```
Career completes
      │
      ▼
Numeric record written to database
(settings vector + policy mode metadata + outcomes vector + waste flag vector)
record_eligibility computed and written
human_directed flag set based on whether any manual input was active
      │
      ▼
  record_eligibility?
      │
      ├── excluded_manual → record stored but excluded from optimizer input
      │                     career outcome still visible in history for human review
      │
      ├── diagnostic_only → record stored; available for LLM and human review only
      │                     must not influence optimizer settings or clean-career means
      │
      ├── observational_learning → enters waste flag rate pool
      │                            must not update clean-career means
      │                            may contribute to native-derived Knowledge Packs
      │
      └── direct_learning → enters full optimizer input pool
                │
                ▼
          Shop learning optimizer runs
          Checks eligible record count → applies tier step limit
          For each settings field:
            — compute waste flag rate (uses direct_learning + observational records)
            — compute clean-career mean (uses ONLY direct_learning records)
            — compute adjustment step toward qualified clean-career mean
            — apply tier step limit
            — apply round_half_away_from_zero()
            — clamp to guardrail min/max
          Output: new settings vector (integers)
                │
                ▼
          New settings applied to deterministic_shop_policy before next career
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
The learning optimizer runs silently every career otherwise.

---

## LLM Exception Layer

The LLM is an exception-only explanation tool. It is not consulted on routine careers.

### When the LLM Is Invoked

Three conditions trigger the LLM. All are exceptional — most careers produce none.

- **Regression:** The 3-career rolling mean of `item_execution_score` drops more
  than 2 points after a learning optimizer adjustment.
- **Novel Flag Combination:** A waste flag combination appears that has no matching
  pattern in the past record database. The learning optimizer cannot compute an
  adjustment step for a combination it has never seen.
- **Human-Requested Explanation:** A human explicitly requests a plain-language
  explanation of a past career's outcomes, a specific waste flag, or why a settings
  adjustment was made.

### What the LLM Receives

When invoked, the LLM receives a structured prompt containing:

1. The trigger reason and which career caused it.
2. The full numeric career record for the triggering career.
3. The last 5 eligible career records, for comparison. For LLM exception prompts,
   "eligible" means records with `record_eligibility` in `direct_learning`,
   `observational_learning`, or `diagnostic_only`. `excluded_manual` and `invalid`
   records are omitted unless a human explicitly requests them.
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

- **Never write configuration values directly.** The shop learning optimizer is
  the sole source of config updates. If a suggested value is applied, the human
  applies it as a manual override, which marks the career `human_directed = 1`.
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

### Knowledge Pack Evidence Type

Every Knowledge Pack must declare how its contributing records were produced.

```json
{
  "schema_version": "1.0.0",
  "optimizer_algorithm_version": "1.0.0",
  "scoring_version": "1.0.0",
  "record_eligibility_version": "1.0.0",
  "ruleset": "umamusume_make_a_new_track",
  "evidence_type": "mixed_policy_evidence",
  "source_policy_modes": ["native", "deterministic", "native_with_deterministic_shadow"],
  "safe_starting_ranges": {},
  "known_failure_conditions": [],
  "conformance_tests": [],
  "conformance_suite_version": null,
  "conformance_suite_hash": null
}
```

| Evidence Type | Meaning |
|---|---|
| `deterministic_policy_evidence` | All contributing records came from runs where the deterministic optimizer made live shop decisions. |
| `native_policy_evidence` | All contributing records came from native-policy runs that emitted compatible telemetry. |
| `mixed_policy_evidence` | Contributing records include both deterministic and native-policy runs. |

This label is required for honest cross-bot learning. Without it, an importing
bot cannot know how much trust to assign the pack.

### Knowledge Pack Trust Levels

Imported Knowledge Packs are assigned a trust level based on their evidence type
and origin. Trust levels determine how aggressively the optimizer weighs imported
knowledge against local records.

```json
{
  "import_trust_level": "external_native_observational"
}
```

| Trust Level | Meaning |
|---|---|
| `local_deterministic_confirmed` | Local records where `deterministic_shop_policy_active = 1` and `universal_profile_source = applied_directly`. Highest trust. |
| `local_native_observational` | Local records where native policy was active. Settings were derived, not directly applied. |
| `external_deterministic_confirmed` | Imported Knowledge Pack with `deterministic_policy_evidence`. |
| `external_mixed` | Imported Knowledge Pack with `mixed_policy_evidence`. |
| `external_native_observational` | Imported Knowledge Pack with `native_policy_evidence`. |
| `external_partial` | Pack imported with one or more unsupported fields omitted. |
| `quarantined` | Pack failed conformance but is retained for diagnostic inspection. |

Trust order (highest to lowest):

```
local_deterministic_confirmed
> local_native_observational
> external_deterministic_confirmed
> external_mixed
> external_native_observational
> external_partial
> expert_seed_defaults
> default_guardrails
> hardcoded_defaults
```

### What Native-Policy Knowledge Packs Can Safely Export

A bot that uses only its native optimizer can still export a Knowledge Pack,
labeled as `native_policy_evidence`. Native-derived packs contribute useful
observational knowledge even without direct deterministic control.

**Safe to export:**

- Recurring waste flag patterns
- Item waste rates
- Safe observed ranges when the adapter's `universal_profile_source` is
  `derived_from_native` (not `defaulted` or `unknown`)
- Known bad threshold combinations
- Item timing failure conditions
- Bootcamp understock patterns
- Climax hammer excess patterns
- Vita never-triggered patterns
- Ankle weight timing problems

**Treat with caution:**

- Exact deterministic optimizer settings (never directly applied)
- Clean-career means (derived from native behavior, not optimizer-controlled runs)
- Strong adjustment recommendations
- High-trust safe ranges

A native-derived pack is useful. It is not proof of causal optimality at the
Universal Shop Profile level. Importing bots should apply it at a lower trust
level than `external_deterministic_confirmed`.

---

## Knowledge Pack Handshake Protocol

Before an importing bot applies a Knowledge Pack, it must prove compatibility
with the exporting bot at the optimizer boundary. This section defines the
five-step validation flow.

The handshake proves that two bots understand the same Universal Shop Profile
fields, compute the same waste flags, compute the same Item Execution score,
and apply the same optimizer adjustment rules. It does not prove gameplay
equivalence, race solver equivalence, or that the pack is optimal.

### Step 1: Schema Validation

The importing bot validates that the Knowledge Pack conforms to the shared schema.
A pack that fails schema validation is rejected immediately — no further steps run.

Required checks:

- All required fields exist and have correct types.
- Unknown fields are rejected unless under a `metadata` key.
- Safe starting ranges are inside global guardrails.
- Known failure condition fields exist in the Universal Shop Profile.
- No raw career records are included.
- No turn-level logs are included.
- No human-directed records are included.
- `evidence_type` is declared.
- `source_policy_modes` is declared.
- No free-text analysis data appears in optimizer-visible fields.

### Step 2: Version Compatibility Check

The importing bot checks:

```
schema_version
optimizer_algorithm_version
scoring_version
record_eligibility_version
ruleset
item_name_mapping_version
```

| Version state | Action |
|---|---|
| Major version differs | Reject the pack |
| Minor version differs | May import in compatibility mode; log a warning |
| Versions match | Proceed |

Major version mismatches indicate incompatible optimizer behavior and must not
be imported.

### Step 3: Capability Check

The importing bot compares the pack's required fields against its own interop
manifest. If a required field is not in `supported_fields`, the bot must either
reject the pack or perform a partial import for explicitly optional fields only.

Partial imports must be labeled with status `partially_applied` and must document
which fields were ignored and why.

Partial imports are never allowed for:

- Core scoring logic
- Waste flag definitions
- Guardrail min/max values
- Item enum mappings
- Optimizer algorithm behavior (step calculation, rounding, clamping order)

Those components must match exactly. A bot that cannot support them must reject
the pack, not silently ignore the mismatch.

### Step 4: Evidence Type Check

The importing bot reads `evidence_type` and assigns the corresponding trust level.

| Evidence type received | Trust level assigned |
|---|---|
| `deterministic_policy_evidence` | `external_deterministic_confirmed` |
| `mixed_policy_evidence` | `external_mixed` |
| `native_policy_evidence` | `external_native_observational` |

A pack with `native_policy_evidence` may still be imported. It is applied at a
lower trust level — useful observational knowledge, but not allowed to override
strong local deterministic evidence.

### Step 5: Conformance Fixture Execution

Every exported Knowledge Pack must provide access to fixtures from each of the
eight required fixture categories. A bot can pass schema validation while failing
scoring, or pass scoring while failing optimizer rounding. Layered fixtures
catch failures at each layer independently.

Fixtures may be provided in one of two ways:

1. **Embedded fixtures** — the full fixture objects are included directly inside the
   Knowledge Pack under the `conformance_tests` key. Suitable for offline portability.
2. **Suite reference** — the Knowledge Pack declares a `conformance_suite_version`
   and `conformance_suite_hash` pointing to a known shared fixture suite. The
   importing bot downloads or locates the suite, verifies its hash, and runs the
   fixtures from the suite rather than from the pack. Suitable for normal use
   where pack size matters.

A pack must use one of these forms. It must not omit both. If `conformance_suite_version`
and `conformance_suite_hash` are present, the importing bot must verify the suite
hash before running any fixtures from it. A suite hash mismatch must be treated
as a `conformance_hash_mismatch` failure.

**Required fixture categories:**

| Fixture Category | What It Proves |
|---|---|
| `schema_fixtures` | Bot validates canonical structure correctly |
| `waste_flag_fixtures` | Bot computes same flags from same career record |
| `scoring_fixtures` | Bot computes same Item Execution score |
| `optimizer_adjustment_fixtures` | Bot updates settings the same way, including rounding |
| `guardrail_fixtures` | Bot clamps values the same way |
| `knowledge_pack_import_fixtures` | Bot accepts/rejects packs consistently |
| `canonical_hash_fixtures` | Bot canonicalizes JSON the same way before hashing |
| `record_eligibility_fixtures` | Bot classifies direct, observational, diagnostic, manual, and invalid records the same way |

Every Knowledge Pack must provide access to at least one fixture from each required category, either through embedded fixtures or a verified conformance suite reference.
A Knowledge Pack that provides only optimizer adjustment fixtures is not
conformance-complete.

Required `record_eligibility_fixtures` examples:
- `deterministic_applied_directly_001` — `shop_policy_mode=deterministic`, `universal_profile_source=applied_directly` → `direct_learning`
- `native_derived_from_native_001` — `shop_policy_mode=native`, `universal_profile_source=derived_from_native` → `observational_learning`
- `manual_override_excluded_001` — `human_directed=1` → `excluded_manual`
- `unknown_profile_diagnostic_001` — `universal_profile_source=unknown` → `diagnostic_only`
- `version_mismatch_diagnostic_001` — `record_eligibility_version` does not match manifest → `diagnostic_only`

**Fixture format:**

```json
{
  "test_id": "climax_hammer_excess_001",
  "fixture_category": "optimizer_adjustment_fixtures",
  "input": {
    "current_profile": {
      "energy_buy_threshold": 40,
      "climax_master_hammer_reserve": 3,
      "climax_artisan_hammer_reserve": 1,
      "master_hammer_buy_cap_turn": 68,
      "glow_sticks_min_fans": 100000,
      "bootcamp_strong_mega_target": 2,
      "coaching_mega_enabled": 0,
      "skill_point_buy_threshold": 300,
      "skill_point_hoard_threshold": 1200,
      "skill_point_force_turn": 62,
      "skill_point_floor": 400,
      "dump_window_start_turn": 64,
      "late_game_save_items": 1,
      "ankle_weights_max_stock": 1
    },
    "career_records": [],
    "manual_direction": null,
    "knowledge_pack_baseline": {}
  },
  "expected_output": {
    "new_profile": {},
    "changed_fields": [],
    "clamped_fields": [],
    "triggered_failure_conditions": [],
    "item_execution_score": 0,
    "conformance_hash": "..."
  }
}
```

The importing bot runs each fixture through its own local implementation of the
corresponding layer. It must produce the same `new_profile`, `changed_fields`,
`clamped_fields`, `triggered_failure_conditions`, `item_execution_score`, and
`conformance_hash`.

If any fixture output differs, the pack fails conformance for that layer. A bot
that fails `scoring_fixtures` should fix its scoring before attempting
`optimizer_adjustment_fixtures`. A failed conformance pack must not be applied.

### Canonical JSON Specification (Shop Optimizer Canonical JSON v1)

Before hashing, the optimizer output must be serialized to canonical JSON using
these exact rules. This is "Shop Optimizer Canonical JSON v1" — not RFC 8785,
not language-default JSON, but a minimal deterministic subset defined here.

- **Encoding:** UTF-8, no BOM
- **Object keys:** Sorted lexicographically by Unicode code point value (U+0000 ascending)
- **Whitespace:** No insignificant whitespace — no spaces after `:` or `,`, no
  indentation, no newlines between values
- **Arrays:** Preserve insertion order (do not sort array elements)
- **Integers:** All optimizer-visible numeric values serialized as JSON integers
  (no decimals, no scientific notation, e.g. `17` not `17.0` or `1.7e1`)
- **Null:** Allowed only where the schema explicitly permits it; absent optional
  fields are omitted entirely rather than serialized as `null`
- **Booleans:** Not used for optimizer-visible fields; use integer 0/1 instead
- **Strings:** UTF-8; key sort uses raw Unicode code point order, no locale normalization
- **Metadata fields:** Excluded from canonical JSON before hashing (see exclusion
  list below)

Example of correctly canonicalized optimizer output:

```json
{"changed_fields":["climax_master_hammer_reserve"],"clamped_fields":[],"item_execution_score":17,"new_profile":{"ankle_weights_max_stock":1,"bootcamp_strong_mega_target":2,"climax_artisan_hammer_reserve":1,"climax_master_hammer_reserve":2,"coaching_mega_enabled":0,"dump_window_start_turn":64,"energy_buy_threshold":40,"glow_sticks_min_fans":100000,"late_game_save_items":1,"master_hammer_buy_cap_turn":68,"skill_point_buy_threshold":300,"skill_point_floor":400,"skill_point_force_turn":62,"skill_point_hoard_threshold":1200},"optimizer_algorithm_version":"1.0.0","schema_version":"1.0.0","scoring_version":"1.0.0","triggered_failure_conditions":[]}
```

Note that `new_profile` keys are sorted lexicographically.

### Conformance Hash

```
conformance_hash = SHA-256(hex) of Shop Optimizer Canonical JSON v1
```

The canonical JSON string is encoded as UTF-8 bytes before hashing. The SHA-256
digest is encoded as a lowercase 64-character hex string. No BOM, no trailing
newline, no whitespace outside the canonical JSON itself.

The `conformance_hash` is computed from the canonical JSON representation of the
optimizer output. The result is encoded as a lowercase hex string.

Hash inputs (must include):

```
new_profile
changed_fields
clamped_fields
triggered_failure_conditions
item_execution_score
optimizer_algorithm_version
scoring_version
schema_version
```

Hash inputs (must exclude):

```
bot name
local file paths
timestamps
human notes
random IDs
execution duration
logging messages
```

This keeps the hash stable across languages, machines, and bot implementations.
Two bots that produce the same hash from the same input apply the same algorithm.

### Import Status Values

Every Knowledge Pack import produces a status.

| Status | Meaning |
|---|---|
| `accepted` | All validation and conformance checks passed. Pack is applied as external baseline. |
| `rejected` | A required check failed. Pack must not affect optimizer behavior. |
| `quarantined` | Pack is stored for diagnostic inspection but not applied. Used when debugging version drift or adapter issues. |
| `partially_applied` | Only explicitly compatible optional subsets were imported. Core checks must still pass. |

### Conformance Failure Categories

| Failure Type | Meaning | Required Behavior |
|---|---|---|
| `schema_mismatch` | Pack structure is invalid or missing required fields | Reject pack |
| `major_version_mismatch` | Major schema, optimizer, or scoring version differs | Reject pack |
| `unsupported_required_field` | Bot cannot represent a required Universal Shop Profile field | Reject pack |
| `item_mapping_mismatch` | Canonical item names or item enums do not match | Reject pack |
| `scoring_mismatch` | Bot computes a different Item Execution score from same input | Reject pack and fix scoring |
| `waste_flag_mismatch` | Bot sets different waste flags from the same input | Reject pack and fix flag logic |
| `optimizer_mismatch` | Same input produces different settings output | Reject pack and fix optimizer |
| `guardrail_mismatch` | Guardrail min/max behavior differs | Reject pack |
| `rounding_mismatch` | Rounding or step calculation order differs | Reject pack |
| `conformance_hash_mismatch` | Output hash differs from fixture | Reject or quarantine until canonical hash logic is fixed |
| `optional_field_unsupported` | Optional field is unsupported by importing bot | Partial import allowed only if explicitly declared safe |

The most critical failures are `scoring_mismatch`, `waste_flag_mismatch`, and
`optimizer_mismatch`. Those mean the two bots are not speaking the same optimizer
language despite using the same field names.

### Required Behavior on Conformance Failure

If any required conformance test fails:

1. Do not apply the Knowledge Pack.
2. Do not update safe starting ranges.
3. Do not update known failure conditions.
4. Do not merge the pack into local optimizer history.
5. Do not use the pack as a clean-career baseline.
6. Store the failed pack as quarantined diagnostic data if desired.
7. Generate an import report.

A failed import leaves the current local optimizer configuration unchanged. It
does not stop the bot from running the next career.

### Import Report

Every import — successful or failed — should produce a machine-readable report
and a human-readable summary.

**Machine-readable (failed example):**

```json
{
  "import_status": "rejected",
  "failure_type": "optimizer_mismatch",
  "failed_test_id": "climax_hammer_excess_001",
  "expected_output": {
    "new_profile": { "climax_master_hammer_reserve": 2 },
    "changed_fields": ["climax_master_hammer_reserve"]
  },
  "actual_output": {
    "new_profile": { "climax_master_hammer_reserve": 3 },
    "changed_fields": []
  },
  "likely_causes": [
    "optimizer step rounding differs from shared spec",
    "guardrail clamp order differs",
    "imported safe baseline was ignored"
  ],
  "pack_applied": false
}
```

**Human-readable summary (failed example):**

```
Knowledge Pack rejected.

Failed test: climax_hammer_excess_001

Expected:
  climax_master_hammer_reserve = 2
  changed_fields = ["climax_master_hammer_reserve"]

Actual:
  climax_master_hammer_reserve = 3
  changed_fields = []

Likely cause:
  Local optimizer did not apply the same adjustment rule as the shared fixture.

Action:
  Pack was not applied. Local optimizer state is unchanged.
```

### Safe Fallback Order After Rejection

A rejected pack must not interrupt normal bot operation. The optimizer continues
using the safest available source:

```
local deterministic records
> local native observational records
> previously accepted deterministic Knowledge Packs
> previously accepted mixed Knowledge Packs
> previously accepted native-derived Knowledge Packs
> expert seed defaults
> default optimizer guardrails
> hardcoded safe defaults
```

### Rule for Coding Agents on Fixture Failures

> When a conformance fixture fails, do not rewrite the expected fixture to match
> the local implementation. Fix the local implementation until it matches the
> shared fixture — unless the fixture itself is proven incorrect against the
> shared spec.

A fixture is an interoperability test, not a local preference test. If every bot
adjusts fixtures to match its own behavior, the shared optimizer system becomes
meaningless.

---

## Expert Seed Defaults

### What Expert Seed Defaults Are

Expert Seed Defaults are hardcoded bootstrap values derived from expert gameplay
analysis. They provide safer initial settings before local `direct_learning`
records or accepted deterministic Knowledge Packs exist. They are not
optimizer-learned data, not clean-career evidence, and not Knowledge Pack
evidence.

Expert Seed Defaults occupy a specific position in the trust hierarchy:

```
local direct_learning records
> accepted external deterministic Knowledge Pack baseline
> expert seed defaults
> default guardrails
> hardcoded safe fallback
```

### What Expert Seed Defaults Must Not Do

Expert Seed Defaults must not:

- count as `direct_learning`
- update clean-career means
- be exported as deterministic Knowledge Pack evidence
- override local direct-learning data
- override accepted deterministic Knowledge Pack baselines
- force race selection or race chaining
- bypass conformance checks

Once at least three local `direct_learning` records exist, the shop learning
optimizer should begin replacing expert seed assumptions with local deterministic
evidence.

### Source Metadata

Expert seed profiles carry source metadata that is excluded from
optimizer-visible numeric analysis and excluded from conformance hashes (unless a
fixture explicitly tests source metadata serialization):

```json
{
  "source_type": "expert_interview_seed",
  "source_name": "rank_1_trackblazer_interview",
  "source_trust_level": "bootstrap_only",
  "source_notes": "Derived from expert race-heavy Trackblazer strategy; not optimizer evidence."
}
```

### Expert Seed Profile: `expert_seed_race_heavy_v1`

This profile is derived from a Rank 1 Trackblazer player interview. The
interview reveals a race-heavy strategy where mood repair items — particularly
Plain Cupcakes and Berry Sweet Cupcakes — are the key inventory layer that
enables longer race chains without rest. Energy items support this by preserving
training capacity. This strategy informs shop/inventory defaults only; race
selection remains outside the scope of this spec.

```json
{
  "profile_name": "expert_seed_race_heavy_v1",
  "source_type": "expert_interview_seed",
  "source_name": "rank_1_trackblazer_interview",
  "source_trust_level": "bootstrap_only",
  "source_notes": "Derived from expert race-heavy Trackblazer strategy; not optimizer evidence.",
  "profile": {
    "energy_buy_threshold": 45,
    "climax_master_hammer_reserve": 2,
    "climax_artisan_hammer_reserve": 1,
    "master_hammer_buy_cap_turn": 62,
    "glow_sticks_min_fans": 100000,
    "bootcamp_strong_mega_target": 2,
    "coaching_mega_enabled": 0,
    "skill_point_buy_threshold": 300,
    "skill_point_hoard_threshold": 1000,
    "skill_point_force_turn": 62,
    "skill_point_floor": 400,
    "dump_window_start_turn": 62,
    "late_game_save_items": 0,
    "ankle_weights_max_stock": 1,
    "mood_item_buy_enabled": 1,
    "mood_item_min_stock": 1,
    "mood_item_max_stock": 2,
    "race_chain_mood_break_after": 4,
    "cupcake_aggression": 2,
    "rest_avoidance_enabled": 1
  }
}
```

**Rationale per field:**

- `energy_buy_threshold = 45` — Supports a rest-averse strategy without
  spending energy items too early. High enough to prevent unnecessary rest turns,
  low enough not to over-buy Vita items.
- `climax_master_hammer_reserve = 2` — Avoids the known over-reservation problem
  where 3 Master Cleat Hammers are held but fewer than 3 Climax races occur.
  See `climax_hammer_excess` waste flag.
- `bootcamp_strong_mega_target = 2` — Supports summer training value without
  overstocking Megaphones.
- `dump_window_start_turn = 62` and `late_game_save_items = 0` — Encourage item
  usage after second summer instead of late-game hoarding.
- `ankle_weights_max_stock = 1` — Conservative because Ankle Weights have several
  possible waste modes (wrong stat, held past bootcamp, no matching training).
- `mood_item_buy_enabled = 1`, `mood_item_min_stock = 1`, `mood_item_max_stock = 2`,
  `cupcake_aggression = 2` — Reflects that cupcakes are a high-value item in a
  race-heavy strategy; the bot should maintain at least one mood item and be
  willing to buy more when available.
- `race_chain_mood_break_after = 4` — After 4 consecutive races, mood repair
  inventory becomes more valuable. Aligns with expert guidance to consider
  breaking race chains at around 4 races.
- `rest_avoidance_enabled = 1` — The expert explicitly states resting is never
  an option; energy and mood items should be weighted more highly to avoid rest
  turns.

### Repository Artifact

The expert seed profile should be stored at:

```
reference/expert_seed_profiles.json
```

This file is machine-readable and may be loaded by implementations to initialize
the optimizer when no direct learning records or accepted deterministic Knowledge
Packs exist.

---

## Record Eligibility Rules

Not all career records contribute equally to learning. Each career record must
include a `record_eligibility` field that classifies how the record may be used.
This field is computed at career end — never set manually.

### Eligibility Values

| Value | Meaning | Allowed Use |
|---|---|---|
| `direct_learning` | Deterministic shop policy was active; Universal Profile was `applied_directly` | Full optimizer learning: clean-career means, safe ranges, waste flag rates, Knowledge Packs |
| `observational_learning` | Native policy was active; profile source is `derived_from_native` | Waste pattern detection, timing diagnostics, lower-trust range contributions, native-derived Knowledge Packs |
| `diagnostic_only` | Profile source is `partially_mapped`, `defaulted`, or `unknown` | Human review, LLM explanation, aggregate diagnostics only — no optimizer influence |
| `excluded_manual` | `human_directed = 1` | Store for history; excluded from all optimizer learning |
| `invalid` | Missing required fields or corrupt telemetry | Ignored by all optimizer and Knowledge Pack export paths |

### Eligibility Computation

```
if human_directed = 1:
    record_eligibility = "excluded_manual"

elif required telemetry fields are missing or corrupt:
    record_eligibility = "invalid"

elif shop_policy_mode = "deterministic"
     AND universal_profile_source = "applied_directly":
    record_eligibility = "direct_learning"

elif shop_policy_mode in ("native", "native_with_deterministic_shadow")
     AND universal_profile_source = "derived_from_native":
    record_eligibility = "observational_learning"

elif universal_profile_source in ("partially_mapped", "defaulted", "unknown"):
    record_eligibility = "diagnostic_only"

else:
    record_eligibility = "diagnostic_only"
```

Shadow mode (`native_with_deterministic_shadow`) produces `observational_learning`
records for the learning optimizer's purposes — the native policy executed the
live decisions, so the profile was derived, not directly applied.

### What Each Eligibility Level Can and Cannot Do

**`direct_learning`** records:
- May update deterministic clean-career means
- May contribute to waste flag rate calculations
- May be used as qualified clean-career baselines in the optimizer adjustment step
- May be included in Knowledge Packs as `deterministic_policy_evidence`

**`observational_learning`** records:
- May contribute to waste flag rate calculations
- May identify timing failure patterns (bootcamp shortage, vita never-triggered, etc.)
- May contribute to native-derived Knowledge Packs as `native_policy_evidence`
- **Must not** update deterministic clean-career means
- **Must not** be used as qualified clean-career baselines

**`diagnostic_only`** records:
- May be surfaced to the LLM exception handler for human-readable explanation
- May be used in aggregate diagnostics (e.g., shop availability heatmaps)
- **Must not** influence optimizer settings or safe ranges in any way

**`excluded_manual`** records:
- Stored for human review and history only
- **Must not** enter any optimizer input pool

**`invalid`** records:
- Discarded from all optimizer and Knowledge Pack paths
- May be logged for adapter debugging

### The Critical Rule

> **Only `direct_learning` records may update deterministic clean-career means.**

This is the single most important rule for cross-bot safety. Without it, native
bot behavior — which may reflect very different heuristics than the Universal
Shop Profile's intended semantics — can contaminate the learning optimizer's
clean baseline and cause the deterministic shop policy to drift toward native
behavior rather than toward genuinely low-waste outcomes.

---

## Recommended Repository Structure

The prose spec should not be the only artifact. A complete implementation should
include machine-readable schemas and golden fixtures that coding agents and
automated tests can use to verify conformance independently of human review.

**Normative authority:** When the prose in this document and a schema file or
conformance fixture disagree, the schema and fixture are authoritative for
implementation behavior. The prose explains intent; the schemas and fixtures
define conformance. Coding agents must resolve contradictions in favor of the
machine-readable artifact, not the prose.

```
shop_optimizer/
  schemas/
    universal_shop_profile.schema.json
    career_record.schema.json
    turn_shop_log.schema.json
    knowledge_pack.schema.json
    interop_manifest.schema.json
    import_report.schema.json
    canonical_items.schema.json

  fixtures/
    schema_fixtures/
      career_record_valid_001.input.json
      career_record_valid_001.expected.json
      career_record_missing_eligibility_001.input.json
      career_record_missing_eligibility_001.expected.json

    waste_flag_fixtures/
      climax_hammer_excess_001.input.json
      climax_hammer_excess_001.expected.json
      skill_point_blocked_001.input.json
      skill_point_blocked_001.expected.json
      vita_never_triggered_001.input.json
      vita_never_triggered_001.expected.json

    scoring_fixtures/
      high_efficiency_001.input.json
      high_efficiency_001.expected.json
      megaphone_waste_deduction_001.input.json
      megaphone_waste_deduction_001.expected.json

    optimizer_adjustment_fixtures/
      climax_hammer_excess_adjustment_001.input.json
      climax_hammer_excess_adjustment_001.expected.json
      skill_point_floor_adjustment_001.input.json
      skill_point_floor_adjustment_001.expected.json
      ankle_weights_bootcamp_001.input.json
      ankle_weights_bootcamp_001.expected.json

    guardrail_fixtures/
      energy_threshold_clamp_001.input.json
      energy_threshold_clamp_001.expected.json
      hammer_reserve_clamp_001.input.json
      hammer_reserve_clamp_001.expected.json

    knowledge_pack_import_fixtures/
      valid_deterministic_pack_001.input.json
      valid_deterministic_pack_001.expected.json
      major_version_mismatch_001.input.json
      major_version_mismatch_001.expected.json
      native_pack_lower_trust_001.input.json
      native_pack_lower_trust_001.expected.json

    canonical_hash_fixtures/
      hash_stable_across_field_order_001.input.json
      hash_stable_across_field_order_001.expected.json
      hash_excludes_metadata_001.input.json
      hash_excludes_metadata_001.expected.json

    record_eligibility_fixtures/
      deterministic_applied_directly_001.input.json
      deterministic_applied_directly_001.expected.json
      native_derived_from_native_001.input.json
      native_derived_from_native_001.expected.json
      manual_override_excluded_001.input.json
      manual_override_excluded_001.expected.json
      unknown_profile_diagnostic_001.input.json
      unknown_profile_diagnostic_001.expected.json

  docs/
    SHOP_OPTIMIZER_SPEC.md
    INTEROP_CONTRACT.md
    KNOWLEDGE_PACK_FORMAT.md
    CONFORMANCE_FAILURES.md
    NATIVE_POLICY_TELEMETRY.md
    RECORD_ELIGIBILITY.md

  reference/
    canonical_items.json          ← IDs, display names, category, cost, held/instant, waste eligibility
    default_guardrails.json
    default_universal_shop_profile.json
    default_policy_modes.json
    rounding_rules.json
    expert_seed_profiles.json     ← bootstrap profiles derived from expert analysis; bootstrap_only trust level
```

The fixtures are the most important files in this structure. The prose spec tells
coding agents what to build. The fixtures prove they built the same thing as every
other conforming bot.

`canonical_items.json` is the authoritative source for all item IDs and metadata.
Any item referenced in telemetry, Knowledge Packs, or fixtures must have a
corresponding entry here. Bots must not invent item IDs — they must map their
internal item representations to IDs defined in this file.

---

## Bot-Agnostic Implementation Checklist

A bot implementation is not complete until it can do all of the following. This
list is the authoritative deliverable specification for any coding agent applying
this spec.

**Policy separation:**
- [ ] Native shop policy preserved as a separate, independently-runnable module (no native code changed except for thin telemetry hooks)
- [ ] Deterministic shop policy implemented as a separate live-decision module
- [ ] Shop learning optimizer implemented as a separate post-career module
- [ ] Shop policy router that dispatches to the selected policy without mixing implementations
- [ ] Frontend or config toggle for `shop_optimizer_mode` supporting at minimum `native` and `deterministic`
- [ ] (Recommended) `native_with_deterministic_shadow` mode supported

**Adapter layer:**
- [ ] Universal Shop Profile adapter translating internal fields ↔ Universal fields
- [ ] Interop manifest generator listing supported/unsupported fields and policy modes
- [ ] Documentation mapping internal config field names to Universal Shop Profile field names
- [ ] Documentation explaining how native-policy records are mapped to canonical telemetry

**Canonical item IDs:**
- [ ] All telemetry fields that reference items use canonical item IDs, not display names
- [ ] Bot maintains a local mapping from internal item names to canonical item IDs
- [ ] Unmapped items are logged as `unknown_item_id` and do not silently use display names
- [ ] Records containing `unknown_item_id` are valid for diagnostics but must not qualify as `direct_learning` or be exported into high-trust Knowledge Packs

**Record eligibility:**
- [ ] `record_eligibility` field computed and written at career end for every career record
- [ ] Learning optimizer filters by `record_eligibility = "direct_learning"` for clean-career means
- [ ] Waste flag rate calculations correctly accept `direct_learning` and `observational_learning`
- [ ] `diagnostic_only`, `excluded_manual`, and `invalid` records excluded from settings influence

**Telemetry:**
- [ ] Career record exporter covering all fields in the Numeric Career Record section
- [ ] Turn-level shop log exporter covering all fields in the Turn-Level Shop Log section
- [ ] Policy mode metadata written correctly for both native and deterministic policies
- [ ] `policy_decision` structured object written for every turn
- [ ] Shadow decision fields written when `shop_optimizer_mode = "native_with_deterministic_shadow"`
- [ ] Telemetry emitter that runs after every turn regardless of which policy made the decision

**Rounding:**
- [ ] All learning optimizer arithmetic uses half-away-from-zero integer rounding
- [ ] Rounding is applied once, at the final `new_value` step — not at intermediate calculations
- [ ] A rounding conformance fixture exists and passes

**Knowledge Pack exchange:**
- [ ] Knowledge Pack exporter with `evidence_type` and `source_policy_modes` declared
- [ ] Knowledge Pack importer with schema validation, version check, and capability check
- [ ] Evidence type check and trust level assignment
- [ ] Conformance fixture runner supporting all 8 fixture categories
- [ ] Knowledge Pack provides access to at least one fixture from each of the 8 required fixture categories, either embedded or through a verified suite reference
- [ ] Conformance hash computation using canonical JSON representation
- [ ] Import report generator (machine-readable and human-readable)
- [ ] Quarantine and reject handling for failed imports

**Expert Seed Defaults:**
- [ ] `reference/expert_seed_profiles.json` loaded as bootstrap when `direct_learning_record_count = 0` and no accepted deterministic Knowledge Pack exists
- [ ] Expert seed defaults applied at lower trust than accepted deterministic Knowledge Packs and never override local `direct_learning` data
- [ ] Expert seed source metadata excluded from conformance hashes

**Verification:**
- [ ] Bot can run native shop policy and emit canonical records
- [ ] Bot can run deterministic shop policy and emit canonical records
- [ ] Bot can run shadow mode and log both active and shadow decisions
- [ ] Bot can switch between policies from frontend or config
- [ ] Bot can export a Knowledge Pack with correct evidence type and fixture categories
- [ ] Bot can import a Knowledge Pack and apply it as external baseline
- [ ] Bot can run the shared conformance fixture suite and produce matching hashes across all 8 categories
- [ ] Bot rejects failed packs safely without disrupting the current career or optimizer state
