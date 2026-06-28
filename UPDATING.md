# UPDATING.md — Post-Update Fork Restoration Guide

When a new upstream version (v3.x) is applied to this repo, use this file to audit
and restore fork-specific changes that the update may have silently reverted.

**Read [UPDATES.md](UPDATES.md) first** — it lists every active fork change and
what's been superseded. This file is the process; UPDATES.md is the inventory.

This is a prompt template. Paste it into a Claude Code conversation after applying
the update commit, then follow the steps.

---

## Step 0: Apply the update

Commit the upstream update as a single commit (e.g. `git commit -m "v3.2"`).
Do NOT mix fork restorations into the same commit — keep the upstream snapshot
clean so it can be diffed against later.

---

## Step 1: Run the audit prompt

Copy-paste the block below into Claude Code. Replace `PREV_COMMIT` with the hash
of the commit immediately before the update (the last fork commit), and `UPDATE_COMMIT`
with the hash of the update commit you just made.

```
I just applied an upstream update to this Icarus fork.

Previous commit (last fork state): PREV_COMMIT
Update commit: UPDATE_COMMIT

Audit every file the update touched against the active fork changes in UPDATES.md.
For each collision, tell me:
  1. What our fork had (with the specific FORK: comment or section)
  2. What the update replaced it with
  3. Your recommendation: keep upstream, restore fork, or merge both — with reasoning

Pay special attention to these DATA CONTRACTS the log viewer depends on. If any
were broken, they MUST be restored:

### Data contract: granular skip reasons (items.py → log_viewer.html)

`_skip_buy()` must return string reason codes, not True/False.
The CALLER at the `elif self._skip_buy(...)` site must pass the string through
as `skip_reason`, not collapse it to a generic "skip_buy".

How to check:
  git diff PREV_COMMIT..UPDATE_COMMIT -- career_bot/items.py | grep -A2 "_skip_buy"
  — if any `return True` / `return False` replaced a `return "reason_string"`, restore the strings
  — if the caller changed from `skip_reason = self._skip_buy(...) or None` to
    `skip_reason = "skip_buy"`, restore the pass-through

Reason codes the log viewer maps (friendlySkipReason):
  auto_buy_cap, user_excluded, skip_wasteful, skip_notepad, skip_inv_cap,
  skip_mega_surplus, skip_anklet_cap, skip_cure_redundant, skip_budget,
  skip_pre_summer, skip_low_deck, skip_buff_used

### Data contract: pre-race item logging (runner.py → log_viewer.html)

The `_race()` method in runner.py must write `bot_pre_race_use_selected` and
`bot_pre_race_use_result` into the career report JSON after `handle_pre_race()`.

How to check:
  git diff PREV_COMMIT..UPDATE_COMMIT -- career_bot/runner.py | grep "bot_pre_race_use"
  — if the FORK block (~16 lines after `_reemit_item_use_debug`) was deleted, restore it

The block to restore (insert after the `self._reemit_item_use_debug(state)` line):

            # FORK: log pre-race item usage to the career report for log_viewer.html
            if self.report and self.item_manager.last_pre_race_use_selected:
                race_turn = int(payload.get("current_turn") or 0)
                target = None
                for t in reversed(self.report.get("turns") or []):
                    if int(t.get("turn") or 0) == race_turn:
                        target = t
                        break
                if not target:
                    for t in reversed(self.report.get("turns") or []):
                        if t.get("stats"):
                            target = t
                            break
                if target:
                    target.setdefault("bot_pre_race_use_selected", []).extend(
                        self.item_manager.last_pre_race_use_selected)
                    target["bot_pre_race_use_result"] = dict(
                        self.item_manager.last_pre_race_use_result)

### Data contract: log_viewer.html must not be deleted

This is a fork-only file. Upstream does not ship it. If the update somehow
removed it, restore from the previous commit.

### Non-collision zone: log_viewer.html internals

The log viewer is never modified by upstream. Do NOT touch its contents during
an update audit. The latest version (with AI summary export, clock display,
dump window analytics, cash-out tracking) is always correct as-is.

---

After the audit, apply ONLY the restorations. Do not modify any upstream code
that doesn't collide with our fork. Commit the restorations separately:
  git commit -m "Restore fork data contracts after vX.Y update"

Then update UPDATES.md:
  - Move superseded fork changes from "Currently Active" to "Superseded"
  - Add a new version entry under "Version History" with collision table
  - Add any new fork changes to "Currently Active"
Also update CLAUDE.md if the "Files Safe to Accept Upstream Wholesale" list changed.
```

---

## Step 2: Verify

After restoration, spot-check:

1. **Python syntax**: `python -c "import ast; ast.parse(open('career_bot/items.py').read())"`
   (repeat for runner.py with `encoding='utf-8'`)
2. **Grep for data contracts**:
   - `grep -n "return \"skip_" career_bot/items.py` — should show 10+ granular reason strings
   - `grep -n "bot_pre_race_use_selected" career_bot/runner.py` — should show the FORK block
   - `test -f log_viewer.html` — must exist
3. **No double-logic**: if upstream added their own version of something we patch
   (e.g. pacing, dump windows), check we're not running both

---

## Collision history

Track which fork changes survived or were superseded across updates. This tells
you what to watch for and what's no longer at risk.

### v3.1 (2026-06-29)

| Fork change | Outcome | Notes |
|---|---|---|
| `_skip_buy()` granular reasons | **Reverted by upstream, restored** | Upstream returned to True/False; we re-applied string reasons |
| `_skip_buy()` caller pass-through | **Reverted by upstream, restored** | Upstream collapsed to `"skip_buy"`; we re-applied `or None` |
| Pre-race item logging (runner.py) | **Deleted by upstream, restored** | 16-line FORK block removed; we re-inserted it |
| `manual_aptitude_overrides` (main.py) | **Superseded by upstream** | v3.1 fixed root cause: UI now sends correct trainee_name/id to solver. Our overlay approach no longer needed |
| `public/app.js` manual overrides | **Superseded by upstream** | Legacy UI (`public/`) replaced by v3 UI (`public-v3/`). Solver aptitude flow redesigned |
| `_pace()` pacing system (runner.py) | **Already gone** | Removed during v3 merge, before v3.1 |
| Megaphone/anklet thresholds | **No collision** | v3.1 didn't change these constants |
| Hammer dump window | **No collision** | v3.1 didn't touch hammer logic |
| `log_viewer.html` | **No collision** | Upstream doesn't ship this file |

### Template for future updates

Copy this table, fill in for the new version:

| Fork change | Outcome | Notes |
|---|---|---|
| `_skip_buy()` granular reasons | | |
| `_skip_buy()` caller pass-through | | |
| Pre-race item logging (runner.py) | | |
| `log_viewer.html` exists | | |
| Megaphone/anklet thresholds | | |
| Hammer dump window | | |
| `_item_cap()` auto_buy priority | | |
| *(add new fork changes here)* | | |

---

## Why this file exists

Upstream updates are applied as whole-commit drops. The author doesn't know about
our fork changes, so every update will silently revert them. CLAUDE.md documents
WHAT we changed and WHY. This file documents HOW to detect and fix reversions
efficiently, including the exact prompt to give Claude Code so it catches everything
in one pass instead of requiring back-and-forth.
