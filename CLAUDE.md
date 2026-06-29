# CLAUDE.md — Icarus Fork Rules

This is a fork of the Icarus bot. Upstream updates arrive as whole-commit drops
that silently revert our changes. Three companion files track the details:

- **[UPDATES.md](UPDATES.md)** — What this fork changed, what's active vs superseded,
  version-by-version collision history. **Read this first when auditing an update.**
- **[UPDATING.md](UPDATING.md)** — Step-by-step process and copy-paste prompt for
  running a post-update audit. Use this every time a new v3.x is applied.
- **[PIRATING.md](PIRATING.md)** — Process for pulling better features from other
  branches or repositories and integrating them into v3-fix.

---

## Core Principle

**Always choose the objectively better behavior.** Not "ours" or "theirs" — the
one that produces better results, measured by run evidence, test outcomes, or
logical analysis. If upstream fixed the same problem better, use theirs. If our
fix is better, keep ours. If both solve different aspects, integrate them as one
cohesive system — never bolt one on top as a bypass.

---

## Coding Rules

1. **Every fork change to bot logic must include a `# FORK: <reason>` comment** (Python)
   or `// FORK: <reason>` (JS). Explains WHY, not what.
2. **Never silently accept either version during a merge.** Compare both against
   the problem documented in UPDATES.md AND run evidence before choosing. Bias
   toward neither — the better fix wins regardless of origin.
3. **Fork changes must integrate with upstream logic, not bypass it.** If upstream
   has a configurable slider, our fix should modify that slider's input or add a
   layer that cooperates with it — not replace it with a hardcoded value the user
   can't control.
4. **Threshold/constant changes are user-tunable.** If upstream changes the same
   constant, prefer the value closer to measured usage (see log viewer reports).
5. **`log_viewer.html` is fork-only.** Upstream does not ship it. Never delete it.
6. **The active UI is `public-v3/`.** The legacy `public/` directory is served at
   `/legacy/` only. Fork changes to `public/app.js` are no longer active.
7. **Every fork change must be logged in [UPDATES.md](UPDATES.md).** Use the exact
   entry format defined at the top of that file. Include date, commit hash, file(s),
   context (the WHY), and status. This is mandatory — if it's not in UPDATES.md,
   it doesn't exist for future audits.
8. **Run the test suite after every merge.** Fork changes that break upstream tests
   must either fix the root cause or adapt the test to the new correct behavior
   (with a `# FORK:` comment explaining why). Silent test regressions are not
   acceptable.

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

1. **Upstream fixes the same bug we fixed?** → Use upstream's version. Delete ours.
2. **Upstream has a better fix for the same problem?** → Use theirs. Log in
   UPDATES.md as SUPERSEDED with evidence why theirs is better.
3. **Our fix is better (with evidence)?** → Keep ours, but integrate it WITH
   upstream's structure. Never bypass upstream's config/slider/toggle — feed into
   it cooperatively.
4. **Both address different problems?** → Integrate as one cohesive system. Our
   fix should modify inputs to upstream's logic, not substitute the output.
5. **Threshold/constant collision?** → Pick whichever results in fewer leftover
   items per run. Use cooperative operations (`min()`, multipliers) over replacement.
6. **New upstream feature, no collision?** → Accept wholesale. Run tests to verify
   our fixes still apply.

### Anti-bias checklist (run this mentally on every collision)

- [ ] Am I keeping ours just because we wrote it?
- [ ] Would I still choose this version if the labels were swapped?
- [ ] Does our fix INTEGRATE with upstream's logic, or BYPASS it?
- [ ] Can the user still control the behavior via upstream's config/sliders?
- [ ] Do the tests still pass?

---

## Files With Active Fork Modifications

These files have ACTIVE fork changes and MUST be audited on every upstream update:

- `career_bot/items.py` — skip reasons, nirio item tuning, MCH reserve, auto_buy cap
- `career_bot/runner.py` — pre-race item logging, nirio run snapshot
- `career_bot/skills.py` — nirio skill forcing (on top of upstream's redesign)
- `career_bot/trackblazer_rules.py` — nirio constants
- `career_bot/scenarios/mant_trackblazer.py` — nirio race chain mood gating
- `public-v3/modals.js` — nirio UI section in Scenario Overrides
- `main.py` — headless ticket sync
- `log_viewer.html` — fork-only, never in upstream

## AI Summary Feedback Loop

When you receive an **AI Summary** from the log viewer (pasted by the user or
read from a career log), compare the run's performance against the current
recommendation in [RECOMMENDED_SETTINGS.md](RECOMMENDED_SETTINGS.md):

1. **Extract** the settings snapshot and performance metrics from the summary.
2. **Compare** against the current recommended values: total stats, win rate,
   Climax mood, item leftovers, SP remaining, coin efficiency.
3. **If the run outperforms** (higher total stats AND better win rate AND fewer
   leftover items), **auto-update** RECOMMENDED_SETTINGS.md:
   - Update the "Current Recommended Settings" tables with the new values.
   - Add a dated entry to "Settings History" with the evidence (metrics).
   - Note which specific settings changed and the measured improvement.
4. **If the run is mixed** (better in some metrics, worse in others), note the
   trade-off in a History entry but do NOT update the recommended values.
5. **If the run underperforms**, add a History entry documenting what was tried
   and why it was worse — this prevents re-trying the same bad settings.

The AI summary includes the full settings snapshot specifically so this feedback
loop can work. Never skip the comparison — every run is data.

---

## Files Safe to Accept Upstream Wholesale

No active fork modifications:
- `career_bot/races.py`, `report.py`, `config_store.py`
- `career_bot/training_scorer.py`, `calibration.py`
- `career_bot/event_bus.py`, `career_bot/events.py`
- All files under `data/`
- All files under `tests/` (but run them after merge to verify)
- `public/styles.css`, `public/index.html`
