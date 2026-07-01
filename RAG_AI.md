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
| Mood | The trainee's current motivation level. Runs from Bad (1) to Normal (2) to Good (3) to Great (4) to Perfect (5). Higher mood improves training results. |
| Stats | The five trainee attributes: Speed, Stamina, Power, Guts, and Wit. |
| Energy (Vitality) | The trainee's current stamina bar for training. Depletes from training, recovers from rest and energy items. Separate from the Stamina stat. |
| Shop | The in-game store where items are purchased using coins. Available on most turns. |
| Coins | The currency used to buy items from the shop. |
| Inventory | Items the bot currently holds. Items stay in inventory until consumed or the career ends. |
| Final Inventory | Items still in inventory at career end. Every item here is waste — coins and turns spent acquiring something that never helped. |
| Bootcamp | The summer training camp that occurs at two fixed windows (early career and mid-career). High-value training turns. Items like Megaphones are most effective here. |
| Climax | The final arc of the career. Contains the highest-grade races. Hammers and Glow Sticks are reserved for use here. |
| Grade 1 Race | The highest tier of regular races. Winning these gives the most fans. |
| Grade 2 Race | Mid-tier races. |
| Grade 3 Race | Lowest tier of regular races. |
| Climax Race | The special races in the final arc. The most important races of the career. |
| Running Style | How the trainee positions during a race: Front Runner, Pace Chaser, Late Surger, or Escape. |
| Bond / Friendship | How close the trainee is to each support card. Higher bond unlocks better training bonuses. |
| Support Cards | The cards selected before the career that determine which trainers appear during training turns. |
| Ailment | A negative status effect on the trainee (Night Owl, Slacker, Skin Outbreak, Slow Metabolism, Migraine, Practice Poor). Each has a specific cure item. |
| Instant-Use Item | An item that is consumed immediately when purchased, on the same turn. It never sits in inventory. |
| Held Item | An item that goes into inventory when purchased and must be manually triggered or automatically triggered by a rule. These can become waste. |
| Dump Window | A late-career period (usually after turn 60–65) where the bot relaxes its buying restrictions and tries to spend remaining coins on useful items before the career ends. |
| RAG | Retrieval-Augmented Generation. A method where an AI searches a memory of past records before answering a question, instead of relying only on what is in the current conversation. |

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

## The Anatomy of a Shop/Item Career Record

Each completed career is stored as one record. Only shop and item data is
captured here — race results and training outcomes belong to the auto solver's
own records.

### Required Fields

**Settings active during this career (shop-relevant only):**
- Energy threshold (what Energy level triggers buying a Vita item)
- Master Cleat Hammer reserve count for Climax
- Artisan Cleat Hammer minimum stock for Grade 2 and Grade 3 races
- Glow Sticks minimum fan count for use
- Bootcamp Megaphone target (how many strong Megaphones to hold before bootcamp)
- Whether Coaching Megaphone buying was enabled
- Skill Point threshold (below this, the bot does not buy skills)
- Dump window start turn (when the bot starts spending aggressively)
- Save items late-game toggle (whether aggressive late spending is on or off)

**Item lifecycle per item type:**
- How many were purchased and on which turns
- How many were consumed, on which turns, and what triggered the use
- How many were in the final inventory (waste count)

**Skill Point trajectory:**
- Skill Points owned at turns 40, 50, 60, 70, and career end
- Total Skill Points spent during the career (zero = critical failure)
- Number of skills purchased

**Coin trajectory:**
- Coins at turn 37 (bootcamp entry)
- Coins at turn 60 (dump window start)
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
issue direction instructions that override the AI's suggestions. This is
intentional — a single run's data can be a statistical outlier, and the human
may have context the AI does not.

### How Manual Direction Works

Before a career starts (or during an active career), the operator can provide
plain-text instructions:

> "This run, prioritize buying Motivating Megaphones before bootcamp even if the
> coin cost is high. Do not buy Coaching Megaphones regardless of what the shop
> shows."

> "Hold exactly 2 Master Cleat Hammers for Climax. Do not use the third one even
> if a Grade 1 race appears after turn 65."

> "If Skill Points exceed 800 before turn 55, force a skill purchase even if the
> hoard threshold has not been reached."

The AI records the manual direction alongside the career record. When future
careers are analyzed, the manual direction is visible so that a result from a
human-directed run is not treated as evidence that the directed behavior is
universally better.

### What Manual Direction Can Override

- Which items to prioritize or deprioritize in the shop
- Item reserve counts (how many of each item to hold back)
- The turn at which to start the dump window
- Whether to buy a specific item category at all (example: disable all Vita
  purchases for one career to test whether the bot needed them)
- Skill Point spending triggers (force early spending, or test hoarding behavior
  explicitly)

### What Manual Direction Cannot Override

- The auto solver's race decisions — those belong to the solver's own system
- The bot's ability to respond to emergencies (example: if the trainee is at zero
  energy before a mandatory race, the bot will still use an energy item even if
  Vita purchases were deprioritized)
- Running style selection — that is separate from this framework

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
