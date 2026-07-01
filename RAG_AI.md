# RAG_AI.md — AI Workflow for Shop and Item Management

This document describes how an AI system should reason about shop purchases and
item usage in a umamusume career bot. It is written in plain game terms so that
it can be understood and applied by any AI agent, regardless of which bot
codebase it is working with.

---

## Scope: What This Document Covers

This framework applies **only to shop and inventory decisions** — when to buy
items, which items to prioritize, when to use items, and how to avoid wasting
them by the end of a career.

It does **not** apply to race selection or race execution. Those decisions are
handled by the bot's auto solver, which already has its own logic for picking
races, choosing running styles, and managing race chains. The AI in this document
is a second layer that sits on top of that solver and focuses exclusively on
the shop.

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
| RAG | Retrieval-Augmented Generation. A method where an AI searches a memory of past records before answering a question, instead of relying only on what is in the current conversation. |

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

## What Problem This AI Framework Solves

The bot's shop logic runs one turn at a time. It scores each available item and
decides whether to buy it based on the current game state. It cannot look
backwards and say: "In the last 15 careers, every time we bought more than two
Vita 20 items before turn 50, at least one of them was still in the final
inventory at career end — we bought too many."

That backward-looking pattern recognition is what this AI layer adds.

The framework has a limited context window — it cannot receive 30 full career
histories in a single prompt. RAG solves this by storing every career run in a
searchable memory and pulling only the most relevant past runs when answering a
question about the current one.

---

## Connecting a Bot to RAG Mode Shop

### The Universal Shop Profile (The Common Language)

Different bots store their shop settings under different internal names, in
different formats, with different value ranges. A bot written in Python with
a JSON config file and a bot written in JavaScript with a database schema cannot
directly compare their settings — even if they are solving the same problem.

RAG Mode Shop solves this by requiring every connected bot to translate its
internal settings into a **Universal Shop Profile** before submitting a career
record. Think of it like currency exchange: Japanese yen and Korean won are
different currencies, but both convert to US dollars for international
transactions. The Universal Shop Profile is the dollar — the common format every
bot speaks when talking to the RAG system.

When the RAG system recommends a settings change, it outputs that recommendation
in the Universal Shop Profile format too. Each bot is then responsible for
translating the recommendation back into its own internal config. The RAG system
never knows or cares what internal names a bot uses — it only speaks the
universal format.

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
| `coaching_mega_enabled` | Boolean | Whether the bot is allowed to buy Coaching Megaphones at all |
| `skill_point_buy_threshold` | Integer | Skill Points must be above this before any skill purchase is considered |
| `skill_point_hoard_threshold` | Integer | Buy skills immediately if Skill Points exceed this, without waiting for the force turn |
| `skill_point_force_turn` | Integer | Turn at which the bot forces skill purchases regardless of Skill Point level |
| `skill_point_floor` | Integer | Minimum Skill Points required for the force-buy to trigger (prevents buying at 0 Skill Points) |
| `dump_window_start_turn` | Integer | Turn at which the bot enters the dump window and relaxes buying restrictions |
| `late_game_save_items` | Boolean | Whether the bot holds items back for future turns during the dump window, or spends aggressively |
| `ankle_weights_max_stock` | Integer | Maximum Ankle Weights of one type to hold in inventory at once |

**Critical warning:** If `skill_point_hoard_threshold` and `skill_point_floor`
are both set above realistic mid-career Skill Point levels, neither skill-buying
trigger can fire. This is the single most destructive configuration mistake — it
causes the bot to finish the career with all Skill Points unspent. The RAG
system will flag this pattern if it has seen it in past records.

### How a Bot Connects

1. At the start of each career, the bot translates its internal settings into the
   Universal Shop Profile and records the active values.
2. At the end of each career, the bot submits the career record to the RAG
   memory, with the Universal Shop Profile attached as the settings snapshot.
3. When requesting analysis, the bot sends the current career's Universal Shop
   Profile. The RAG system retrieves past records with matching or similar
   profiles and returns its findings in Universal Shop Profile terms.
4. If the RAG system recommends changing `energy_buy_threshold` from 40 to 55,
   the bot translates that back to whatever its internal config calls that setting
   and applies the change.

The bot's internal logic does not change. Only the translation layer at the
boundary changes.

---

## The Anatomy of a Shop/Item Career Record

Each completed career is stored as one record in the RAG memory. Only shop and
item data is captured here — race results and training outcomes belong to the
auto solver's own records.

### Required Fields

**Settings snapshot:** The Universal Shop Profile values that were active during
this career (see table above). This is what the RAG system uses to find past
records with similar configurations.

**Item lifecycle per item type:**
- How many were purchased and on which turns
- How many were consumed, on which turns, and what triggered the use
- How many were in the final inventory (waste count)

**Skill Point trajectory:**
- Skill Points owned at turns 40, 50, 60, 70, and career end
- Total Skill Points spent during the career (zero = critical failure)
- Number of skills purchased

**Coin trajectory:**
- Coins at turn 37 (first bootcamp entry)
- Coins at turn 60 (second bootcamp entry / dump window start)
- Coins at career end (leftover = wasted purchasing power)

**Final inventory (the waste report):**
- Every item type and count still owned at career end
- Estimated coin value of wasted items

**Known issues flagged for this career:**
- Free-text notes added during or after the run (e.g., "Skill Point buying
  completely failed — hoard threshold never reached")

### Tags for Fast Retrieval

Tags allow the AI to find relevant past records without reading the full entry.
A record can have multiple tags.

| Tag | When to apply |
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
| `sp_catchall_blocked` | Both the Skill Point hoard threshold and the Skill Point floor threshold were above realistic mid-career Skill Point levels simultaneously, blocking all skill buying |
| `vita_never_triggered` | Vita items were purchased but the energy threshold was never breached — bot bought energy items it had no reason to use |

---

## How RAG Works for Shop Decisions

When the bot completes a career, the AI receives the current run's shop record
and asks the memory for the most relevant past records before writing its
analysis.

### Example Retrievals

**Situation:** 4 Master Cleat Hammers remain in the final inventory after a
career with only 2 Climax races.

The AI queries the memory: "Past careers where Master Cleat Hammer count in final
inventory was greater than 1."

Retrieved records show: in 4 of the last 6 careers with this pattern, the Climax
had fewer races than expected (2 instead of 3). The Master Cleat Hammer reserve
policy was protecting for 3 Climax races but only 2 ran. The AI identifies this
as a systemic over-protection pattern, not a one-off error.

---

**Situation:** Skill Points remaining at career end is 100. Zero skills were
purchased.

The AI queries: "Past careers with the `skill_buy_failure` or `skill_point_hoard`
tag."

Retrieved records show: the same failure appears in 3 past careers, all of which
had the Skill Point hoard threshold set above 1400 AND the Skill Point floor
threshold set above 1000 at the same time. This creates a situation where neither
buying trigger can fire — the bot accumulates Skill Points but never crosses the
hoard threshold, and at the force-buy turn the floor threshold blocks it too.
The AI names this as the "Skill Point catch-22" and recommends lowering one of
the two thresholds.

---

**Situation:** 5 Vita 20 items appear in the final inventory.

The AI queries: "Past careers with the `vita_waste` or `vita_never_triggered`
tag."

Retrieved records show: in the matching past careers, the bot had its energy
threshold set lower than the level at which training actually depletes energy.
The bot bought Vita 20 as insurance but the energy level never dropped far
enough to trigger use. The AI recommends raising the energy threshold or reducing
how many Vita 20 items are allowed in inventory at once.

---

## Manual Direction Input

The AI does not have final authority over shop decisions. The human operator can
submit numerical ratings before or during a career to shift the AI's behavior.
Ratings are numbers only — no verbal instructions — so the AI can use them
directly in its scoring without needing to interpret language.

### The Rating Scale

All priority ratings use this five-point scale:

| Rating | Meaning |
|---|---|
| +2 | Maximize. Treat this as the highest-priority concern this career, even at cost to others. |
| +1 | Increase. Weight this more than the AI's default recommendation. |
|  0 | Default. Follow the AI's recommendation based on past records. |
| -1 | Reduce. Weight this less than the AI's default recommendation. |
| -2 | Suppress. Treat this as the lowest-priority concern this career, or disable it entirely. |

### Priority Ratings (What to Emphasize)

These rate how much the human wants to emphasize a strategic dimension relative
to the AI's default weighting. A rating of 0 on every dimension means "do
exactly what the AI recommends."

| Dimension | What it controls |
|---|---|
| `energy_priority` | How aggressively to buy and use Vita items and Royal Kale Juice |
| `mood_priority` | How aggressively to buy and use Cupcakes for Mood repair |
| `bootcamp_mega_priority` | How aggressively to stock Motivating and Empowering Megaphones before turn 37 |
| `hammer_conservation` | How strictly to protect Master Cleat Hammers from being used before Climax |
| `skill_spending_urgency` | How urgently to push Skill Point spending earlier in the career |
| `dump_aggression` | How aggressively to spend remaining coins once the dump window opens |
| `ankle_weights_priority` | How aggressively to buy and time Ankle Weights around bootcamp windows |
| `coaching_mega_priority` | Whether to buy Coaching Megaphones at all (-2 = never buy, +2 = buy freely) |

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

This tells the AI: buy fewer energy items than usual, but be very aggressive
about Mood repair; stock Megaphones and push Skill Point spending earlier; never
buy Coaching Megaphones this run.

### Value Overrides (Exact Numbers)

These pin a specific Universal Shop Profile field to an exact value, bypassing
the AI's recommendation entirely. Use these when you want a precise behavior,
not just a relative emphasis.

| Override Field | Example | Effect |
|---|---|---|
| `climax_master_hammer_reserve` | `= 2` | Hold exactly 2 Master Cleat Hammers for Climax, regardless of how many Climax races are expected |
| `climax_artisan_hammer_reserve` | `= 1` | Hold exactly 1 Artisan Cleat Hammer as fallback |
| `bootcamp_strong_mega_target` | `= 3` | Hold exactly 3 strong Megaphones going into the first bootcamp |
| `skill_point_force_turn` | `= 55` | Force Skill Point spending at turn 55 instead of the AI's recommended turn |
| `dump_window_start_turn` | `= 62` | Start the dump window at turn 62 regardless of coin level |
| `master_hammer_buy_cap_turn` | `= 60` | Stop buying new Master Cleat Hammers after turn 60 |

Value overrides take precedence over priority ratings. If you set
`climax_master_hammer_reserve = 2` and also set `hammer_conservation: +2`, the
exact value of 2 is used — the +2 rating does not increase it further.

### How Ratings Are Recorded

The career record stores the full rating input exactly as submitted. When future
careers are analyzed, the AI checks whether the ratings were non-zero. If any
rating deviates from 0, the career is flagged as **human-directed** and excluded
from the pool used to update confirmed failure patterns or safe starting ranges.

The AI will still report whether the run produced good or bad outcomes, but it
will not treat a human-directed run as evidence that the directed behavior is
universally better. A human-directed run is an experiment, not a data point for
the baseline.

### What Ratings Cannot Override

- The auto solver's race decisions — those belong to the solver's own system.
- Emergency energy use before a mandatory race — if the trainee has zero Energy
  before a race the bot cannot skip, it will use an energy item regardless of
  `energy_priority` rating.
- Running style selection — that is separate from this framework.

---

## The Run Score for Shop Performance

The composite run score described in the full AI workflow framework has one pillar
that directly measures shop and item performance: **Item Execution.**

Item Execution is scored 0–20 based on:
- Items consumed divided by items purchased, weighted by item value
- Master Cleat Hammers and Vita items count more than Reset Whistles or Good-Luck
  Charms — wasting a 40-coin Master Cleat Hammer is a larger penalty than wasting
  a 20-coin Reset Whistle
- Zero Master Cleat Hammers or Vita items in final inventory = full points for
  that sub-category
- Every Motivating Megaphone or Empowering Megaphone in final inventory after
  turn 65 subtracts heavily from the score

A career that bought 20 items and used all 20 scores higher on this pillar than
one that bought 30 items and used 25. Buying less but using all of it is better
than buying more and wasting some.

---

## The Feedback Loop

```
Career completes
      │
      ▼
Shop/item record saved to RAG memory
(settings + item lifecycle + Skill Point trajectory + coin trajectory + tags)
      │
      ▼
AI retrieves 3–5 past records matching current run's failure tags or settings pattern
      │
      ▼
AI compares current run against retrieved records:
  — Is this a known failure mode? (appears in 3+ past records with same tag)
  — Is this better or worse than similar past runs on item execution?
  — What repeatable rule would reduce waste or improve Skill Point spending?
  — Does the human's manual direction explain any unusual outcome?
      │
      ▼
Human reviews AI output
      │
      ├── Finding is valid + actionable → adjust the relevant shop setting
      │   and note the change in the run history
      │
      └── Finding is a one-off or explained by manual direction →
          add a note to the record and move on
                  │
                  ▼
          New career starts with updated or confirmed settings
```

---

## Exportable Learnings (Community Knowledge Packs)

### The Problem With Starting From Zero

A new user who just connected their bot to RAG Mode Shop has an empty memory.
The RAG system has no past records to retrieve, so it cannot recognize known
failure modes or suggest safe starting ranges. They would need to run many
careers before the memory becomes useful — repeating mistakes that the community
already solved months ago.

### What a Knowledge Pack Is

A Knowledge Pack is an export of the accumulated learnings from a RAG memory,
stripped of any personal career data. It contains only the distilled conclusions,
not the raw career records themselves.

A Knowledge Pack contains three things:

**1. Confirmed Failure Patterns**
Patterns that have been observed in 3 or more independent careers and confirmed
as systemic — not a one-off. Each entry includes the failure tag, the Universal
Shop Profile values that were active when the failure occurred, and a plain
description of why the failure happened.

Example:
> **Tag:** `sp_catchall_blocked`
> **Observed in:** 3 careers across 2 users
> **Profile values at failure:** `skill_point_hoard_threshold` ≥ 1400 AND
> `skill_point_floor` ≥ 1000
> **Why:** Both thresholds were above realistic mid-career Skill Point levels.
> Neither trigger could fire. All Skill Points were unspent at career end.
> **Recommendation:** Set `skill_point_hoard_threshold` ≤ 1000 and
> `skill_point_floor` ≤ 500.

**2. Safe Starting Ranges**
For each Universal Shop Profile field, the range of values that has produced
Item Execution scores above 15 out of 20 across all contributing careers.
These are not the "best" values — they are the range that avoids known waste
patterns. A new user can start within this range and tune from there.

Example:
> `energy_buy_threshold`: safe range 35–50
> `climax_master_hammer_reserve`: safe range 2–3
> `bootcamp_strong_mega_target`: safe range 2–3
> `skill_point_hoard_threshold`: safe range 800–1200
> `skill_point_force_turn`: safe range 55–65

**3. High-Waste Item Patterns**
Which items most frequently appear in final inventories, and under what Universal
Shop Profile conditions. New users can immediately guard against the most common
waste sources.

Example:
> Master Cleat Hammers left over: most common when `climax_master_hammer_reserve`
> = 3 but only 2 Climax races ran. Consider `climax_master_hammer_reserve` = 2
> as the default with a conditional bump to 3 only when all 3 Climax races are
> confirmed.
>
> Vita 20 left over: most common when `energy_buy_threshold` is set below 35.
> Bot buys energy items that are never needed because training turns don't deplete
> Energy far enough.

### What a Knowledge Pack Does NOT Contain

- Raw career records or turn-by-turn data (those are private to each user)
- Any information about which trainee, scenario, or support card deck was used
  (those affect results but belong to the auto solver's domain, not the shop)
- Settings that were only tested by a single user in a single career (too little
  evidence to include)
- Manual-direction career results (those are flagged as non-standard in the
  career record and are excluded from pattern analysis)

### Sharing and Importing

A Knowledge Pack is a single file that can be shared between users. Importing a
pack does not replace the user's own memory — it merges the confirmed failure
patterns and safe ranges into the existing memory, weighted lower than locally
observed evidence. A locally observed pattern with 3 confirmations carries more
weight than the same pattern imported from a pack, since the local environment
(trainee, scenario, support deck) may differ.

When importing, the RAG system notes the source of each imported pattern. If a
local career later contradicts an imported pattern, the local observation wins
and the imported entry is flagged for review.

---

## What the AI Should Never Do

- **Never execute purchases directly.** The bot's shop logic is the authority.
  The AI produces advisory text only.
- **Never promote a manual-direction run as evidence of optimal settings.**
  A run where the human forced specific behavior proves only that the forced
  behavior produced that result under those conditions.
- **Never clear failure records from the memory.** Past records tagged with
  `skill_buy_failure`, `master_cleat_waste`, or similar are the most valuable
  entries in the memory. They are what let the AI recognize when a new run is
  repeating a known mistake.
- **Never recommend buying a specific item just because it appeared in a
  high-scoring past run.** The right item depends on the current game state,
  coin budget, and career phase — not on what was bought in a past career with
  different support cards or a different trainee.
- **Never conflate instant-use items with held items when measuring waste.**
  Instant-use items (Notepads, Manuals, Scrolls, Grilled Carrots, and others)
  cannot be wasted — they are consumed the moment they are purchased. Waste
  analysis only applies to held items that sit in inventory.
