# UPDATING.md — Post-Update Fork Integration Process

Step-by-step process for auditing and integrating fork changes after an upstream
version bump. The goal is NOT to blindly restore our code — it's to pick the
better behavior for each collision and integrate it properly.

**[UPDATES.md](UPDATES.md)** is the inventory — what changed, when, why, and
whether it's still active. Read it first. This file is the how-to.

---

## Step 0: Apply the update

Commit the upstream update as a single commit (e.g. `git commit -m "v3.2"`).
Do NOT mix fork integrations into the same commit — keep the upstream snapshot
clean so it can be diffed against later.

---

## Step 1: Run the test suite BEFORE any changes

```
pytest tests/ -v 2>&1 | tee test_baseline.txt
```

This captures upstream's test state. If upstream's own tests fail, that's their
bug — note it but don't fix it in the integration commit.

---

## Step 1.5: Read the upstream CHANGELOG

```
git show <UPDATE_COMMIT> -- CHANGELOG.md | head -80
```

Read the top of CHANGELOG.md for the new version heading. This tells you what
upstream INTENDED to change. Any collision that upstream's changelog doesn't
mention is an accidental revert of our fork work (restore ours). Any collision
that the changelog explicitly addresses is a deliberate upstream change — compare
both versions against the evidence before deciding.

---

## Step 2: Run the audit prompt

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
  3. Your recommendation using the BEHAVIOR COMPARISON below — not "keep ours"
     by default, but which version is objectively better and how to integrate it

BEHAVIOR COMPARISON (do this for every collision):
  - What problem does OUR version solve? What's the evidence it works?
  - What problem does UPSTREAM's version solve? What's new/better about it?
  - Does our fix BYPASS upstream logic (bad) or INTEGRATE with it (good)?
  - If ours is better: can it be rewritten to COOPERATE with upstream's config
    (use their slider as input, use min/max/multiplier instead of replacement)?
  - If theirs is better: mark ours SUPERSEDED and delete it cleanly.
  - Run the anti-bias checklist from CLAUDE.md on each decision.

Pay special attention to these DATA CONTRACTS the log viewer depends on. If any
were broken, they MUST be restored (these are non-negotiable):

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

After the audit, apply ONLY the integrations. Do not modify any upstream code
that doesn't collide with our fork. Commit the integrations separately:
  git commit -m "Integrate fork fixes after vX.Y update"

Then update UPDATES.md:
  - Add a dated entry for the upstream update (status: N/A, upstream snapshot)
  - Add a dated entry for the integration commit (status: ACTIVE)
  - For each collision: record WHICH behavior won and WHY (evidence/logic)
  - Move any superseded fork changes' status to SUPERSEDED
  - Add a collision summary table under "Collision Summary by Version"
Also update CLAUDE.md if the "Files With Active Fork Modifications" list changed.
```

---

## Step 3: Verify integration quality

After integration, check that fixes COOPERATE with upstream, not bypass it:

1. **No bypass pattern**: grep for our FORK blocks and verify each one feeds INTO
   upstream logic (modifies inputs, uses `min()`/`max()`, reads upstream config)
   rather than replacing upstream's output with a hardcoded value.
2. **User controls still work**: for every upstream slider/toggle we touch, verify
   the user can still change the setting and see an effect.
3. **Python syntax**: `python -c "import ast; ast.parse(open('<file>').read())"`
4. **Grep for data contracts**:
   - `grep -n "return \"skip_" career_bot/items.py` — should show 10+ granular reason strings
   - `grep -n "bot_pre_race_use_selected" career_bot/runner.py` — should show the FORK block
   - `test -f log_viewer.html` — must exist

---

## Step 4: Run tests AFTER integration

```
pytest tests/ -v 2>&1 | tee test_after.txt
diff test_baseline.txt test_after.txt
```

- Tests that passed before and fail now → our integration broke something. Fix it.
- Tests that failed before and still fail → upstream's bug, not ours. Ignore.
- Tests that test upstream behavior we intentionally changed → adapt the test with
  a `# FORK:` comment explaining the new correct behavior.

---

## Collision Summary Template

Copy this table for new versions. Fill in from the audit results.

### vX.Y (YYYY-MM-DD)

| Fork change | Winner | Integration |
|---|---|---|
| `_skip_buy()` granular reasons | | |
| `_skip_buy()` caller pass-through | | |
| Pre-race item logging (runner.py) | | |
| Nirio skill forcing | | |
| Nirio mood floor / cupcake | | |
| Nirio item dump windows | | |
| Dynamic MCH reserve | | |
| Nirio race chain mood gating | | |
| Headless ticket sync | | |
| `_item_cap()` auto_buy priority | | |
| `log_viewer.html` exists | | |
| *(add new fork changes here)* | | |

**Winner** column: `OURS`, `THEIRS`, or `MERGED` (both contribute).
**Integration** column: how the winning behavior was integrated (cooperative, not bypass).

---

## Why this file exists

Upstream updates are applied as whole-commit drops. The author doesn't know about
our fork changes, so every update will silently revert them. UPDATES.md documents
WHAT and WHEN. This file documents HOW to evaluate and integrate efficiently,
picking the better behavior every time — not blindly restoring ours.
