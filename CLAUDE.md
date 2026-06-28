# CLAUDE.md — Icarus Fork Rules

This is a fork of the Icarus bot. Upstream updates arrive as whole-commit drops
that silently revert our changes. Two companion files track the details:

- **[UPDATES.md](UPDATES.md)** — What this fork changed, what's active vs superseded,
  version-by-version collision history. **Read this first when auditing an update.**
- **[UPDATING.md](UPDATING.md)** — Step-by-step process and copy-paste prompt for
  running a post-update audit. Use this every time a new v3.x is applied.

---

## Coding Rules

1. **Every fork change to bot logic must include a `# FORK: <reason>` comment** (Python)
   or `// FORK: <reason>` (JS). Explains WHY, not what.
2. **Never silently revert a fork change during a merge.** Compare both versions
   against the problem documented in UPDATES.md before choosing.
3. **Threshold/constant changes are user-tunable.** If upstream changes the same
   constant, prefer the value closer to measured usage (see log viewer reports).
4. **`log_viewer.html` is fork-only.** Upstream does not ship it. Never delete it.
5. **The active UI is `public-v3/`.** The legacy `public/` directory is served at
   `/legacy/` only. Fork changes to `public/app.js` are no longer active.

---

## Data Contracts (must survive every update)

These are the backend→frontend contracts that the log viewer depends on.
If an update breaks any of these, the log viewer silently loses features.

### 1. Granular skip reasons (`items.py` → `log_viewer.html`)

`_skip_buy()` returns string reason codes, not booleans.
The caller passes the string through as `skip_reason`, not a generic `"skip_buy"`.
`friendlySkipReason()` in the log viewer maps these strings to display labels.

### 2. Pre-race item logging (`runner.py` → `log_viewer.html`)

The FORK block in `_race()` writes `bot_pre_race_use_selected` into the career
report JSON after `handle_pre_race()`. Without it, hammer/glow stick usage on
race turns is invisible in the log viewer.

### 3. `log_viewer.html` exists

Fork-only file. Must not be deleted by any update. Contains AI summary export,
skip reason breakdown, pre-race timeline, and all client-side analytics.

---

## Merge Decision Framework

When upstream updates a function we've modified:

1. **Upstream fixes the same bug we fixed?** → Use upstream's version.
2. **Upstream breaks our fix?** → Keep ours. Check UPDATES.md for the invariant.
3. **Both address different problems?** → Take upstream's structure, re-apply our fix on top.
4. **Threshold/constant collision?** → Pick whichever results in fewer leftover items per run.
5. **New upstream feature, no collision?** → Accept wholesale. Verify our fixes still apply.

---

## Files Safe to Accept Upstream Wholesale

No active fork modifications:
- `career_bot/skills.py`, `races.py`, `report.py`, `config_store.py`
- `career_bot/training_scorer.py`, `calibration.py`
- `career_bot/scenarios/mant_trackblazer.py`
- All files under `data/`
- All files under `tests/`
- All files under `public-v3/` (we have no v3 UI modifications)
- `public/styles.css`, `public/index.html`
- `main.py` (no active fork changes since v3.1 superseded ours)
