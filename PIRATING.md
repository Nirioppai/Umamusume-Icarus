# PIRATING.md — Stealing Better Features From Other Branches

Process for pulling features from other branches or repositories and integrating
them into `v3-fix`. The goal: if someone else built something better, take it.

Referenced by [CLAUDE.md](CLAUDE.md) (rules).

---

## When to pirate

- Another branch or repo has a feature we don't have and want.
- Another branch solved the same problem we solved, but better.
- A community fork has optimizations we can measure and verify.

## When NOT to pirate

- The feature conflicts with our core behavior and we'd have to gut our fixes.
- The feature has no tests, no evidence, and no documentation — too risky.
- The source is a tagged release branch (use [UPDATING.md](UPDATING.md) instead).

---

## Step 0: Add the source branch as a remote (if external)

For branches in this repo:
```
git fetch origin <branch-name>
```

For external repos:
```
git remote add <name> <url>
git fetch <name>
```

Do NOT tag pirated branches as `vX.X.X` — those are reserved for upstream updates
via UPDATING.md. Use descriptive names like `pirate/<source>/<feature>`.

---

## Step 1: Identify what to steal

```
git diff v3-fix..<source-branch> --stat
```

List the files and features you want. For each feature, answer:

1. **What does it do?** One sentence.
2. **Do we already have something similar?** If yes, which is better?
3. **Does it touch files we've modified?** If yes, collision audit needed.
4. **Does it have tests?** If yes, do they pass on the source branch?

---

## Step 2: Cherry-pick or extract

**Option A: Clean cherry-pick** (feature is in a single commit)
```
git cherry-pick --no-commit <hash>
```
Review the staged changes. Remove anything that conflicts with our fixes.

**Option B: File-level extraction** (feature spans multiple commits)
```
git show <source-branch>:<path/to/file> > /tmp/pirated_file.py
```
Diff against our version. Extract only the functions/blocks you want.

**Option C: Diff-guided integration** (feature touches files we've modified)
```
git diff v3-fix..<source-branch> -- <file>
```
Read the diff. Apply only the hunks that are the feature, skip the ones that
would revert our fixes. This is the most common case.

---

## Step 3: Behavior comparison (same as UPDATING.md)

For every pirated feature that touches code we've modified:

- What problem does THE PIRATED version solve?
- What problem does OUR version solve?
- Does the pirated version BYPASS our logic or INTEGRATE with it?
- Which produces better results? (run evidence, test outcomes, logical analysis)

Apply the anti-bias checklist from CLAUDE.md. The pirated version wins if it's
better — even if that means deleting our code.

---

## Step 4: Run tests

```
pytest tests/ -v
```

- Pirated features that break existing tests → fix the integration, not the test.
- Pirated features that come with their own tests → include those tests.
- If the pirated feature changes behavior our tests verify → adapt the test with
  a `# FORK:` comment explaining the new correct behavior.

---

## Step 5: Log in UPDATES.md

Use the standard entry format with an additional **Source** field:

```
### YYYY-MM-DD — <short title>
**Commit:** `<hash>` **File(s):** `<path>`
**Source:** Pirated from `<branch>` @ `<hash>` (<repo if external>)
**Context:** <why we took this — what problem it solves better than our version>
**Status:** ACTIVE
```

---

## Step 6: Verify integration quality

Same as UPDATING.md Step 3:

1. No bypass pattern — pirated code feeds INTO our logic, not around it.
2. User controls still work — pirated feature respects our config/sliders.
3. Tests pass.
4. Data contracts intact (skip reasons, pre-race logging, log_viewer.html).

---

## Pirate log

Track what was pirated, from where, and when. Newest first.

*(No entries yet)*
