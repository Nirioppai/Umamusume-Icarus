# UPDATING.md — Post-Update Fork Restoration Process

Step-by-step process for auditing and restoring fork changes after an upstream
version bump.

**[UPDATES.md](UPDATES.md)** is the inventory — what changed, when, why, and
whether it's still active. Read it first. This file is the how-to.

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

Audit every file the update touched against the ACTIVE fork changes in UPDATES.md.
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
  - Add a dated entry for the upstream update (status: N/A, upstream snapshot)
  - Add a dated entry for the restoration commit (status: ACTIVE)
  - Move any superseded fork changes' status to SUPERSEDED
  - Add a collision summary table under "Collision Summary by Version"
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

## Collision Summary Template

Copy this table for new versions. Fill in from the audit results.

### vX.Y (YYYY-MM-DD)

| Fork change | Outcome |
|---|---|
| `_skip_buy()` granular reasons | |
| `_skip_buy()` caller pass-through | |
| Pre-race item logging (runner.py) | |
| Megaphone/anklet thresholds | |
| Hammer dump window | |
| `_item_cap()` auto_buy priority | |
| `log_viewer.html` exists | |
| *(add new fork changes here)* | |

---

## Why this file exists

Upstream updates are applied as whole-commit drops. The author doesn't know about
our fork changes, so every update will silently revert them. UPDATES.md documents
WHAT and WHEN. This file documents HOW to detect and fix reversions efficiently,
including the exact prompt to give Claude Code so it catches everything in one pass.
