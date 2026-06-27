# Codebase Structure

**Analysis Date:** 2026-06-27

## Directory Layout

```
Umamusume-Icarus/
├── main.py                 # FastAPI server, API routes, auth, career orchestration (7,787 lines)
├── manager.py              # Multi-instance process supervisor (272 lines)
├── run.bat                 # Windows launcher (venv + deps + start)
├── settings.json           # Default settings (turn_delay, tp_recovery)
├── requirements.txt        # Python dependencies
├── package.json            # Node.js deps (steam-user for ticket generation)
├── career_bot/             # Domain logic package — strategy, scoring, AI
│   ├── scenarios/          # Scenario strategy implementations
│   │   ├── base.py         # Decision dataclass + ScenarioStrategy ABC
│   │   ├── mant.py         # MantStrategy (Scenario 4) — primary strategy (1,834 lines)
│   │   └── mant_trackblazer.py  # Trackblazer extensions for Mant (632 lines)
│   ├── runner.py           # CareerRunner — threaded career execution engine (4,049 lines)
│   ├── races.py            # RacePlanner — schedule solver with live replanning (977 lines)
│   ├── skills.py           # SkillBuyer — skill purchase logic (1,453 lines)
│   ├── items.py            # MantItemManager — consumable item economy (1,913 lines)
│   ├── events.py           # EventManager — event choice resolution (776 lines)
│   ├── training_scorer.py  # TrainingScorer — heuristic training scorer (832 lines)
│   ├── trackblazer.py      # Smart race solver + external data sync (2,141 lines)
│   ├── trackblazer_guide.py # Trackblazer guide data loader
│   ├── trackblazer_rules.py # Trackblazer constraint rules
│   ├── master_data.py      # SQLite reader for game's master.mdb (2,334 lines)
│   ├── config_store.py     # ConfigStore — preset CRUD with 3 config planes (538 lines)
│   ├── presets.py           # Preset hydration/serialization helpers
│   ├── ai_dataset.py       # JSONL career data export for analytics (1,445 lines)
│   ├── ai_advisor.py       # Beta-Binomial race outcome advisor (721 lines)
│   ├── ai_trainer.py       # Background auto-training + model builder (1,605 lines)
│   ├── ai_modeling.py       # Bayesian modeling primitives (303 lines)
│   ├── local_llm.py        # Optional local LLM adapter (733 lines)
│   ├── policy_guards.py    # Safety rails for learned adjustments (248 lines)
│   ├── delay.py            # Human-like timing delays with DNA seed
│   ├── report.py           # Career report builder + AI dataset export trigger
│   ├── discord_logger.py   # Discord webhook telemetry (283 lines)
│   ├── diagnostics.py      # Runtime diagnostics helpers
│   ├── calibration.py      # Scoring calibration utilities (362 lines)
│   ├── character_data.py   # Character preset + epithet catalog loaders (666 lines)
│   ├── character_profiles.py # Character profile resolution (666 lines)
│   ├── dynamic_skill_profiles.py # Dynamic skill profile generation
│   ├── event_outcomes.py   # Event outcome knowledge base (571 lines)
│   ├── race_intelligence.py # Runtime race outcome recording (243 lines)
│   ├── recommended_stats.py # Recommended stat build loader
│   ├── regret_replay.py    # Counterfactual regret analysis (479 lines)
│   ├── running_style.py    # Running style resolution helpers
│   └── style_adaptation.py # Running style adaptation from data (885 lines)
├── uma_api/                # Game server transport layer
│   ├── client.py           # UmaClient — AES-encrypted msgpack API client (1,126 lines)
│   └── career_recovery.py  # Resume in-progress career after 102 errors (82 lines)
├── data/                   # Static game data and user config
│   ├── *.json              # 52+ JSON catalogs (races, skills, events, items, etc.)
│   ├── character_data/     # Community-maintained character presets + epithets
│   ├── character_profiles/ # Per-character profile JSON files
│   ├── presets/            # User career presets (migrated to userdata on first run)
│   ├── trackblazer/        # Race agendas, races, epithets, debut races
│   ├── images/             # Character card images (PNG)
│   └── skill_icons/        # Skill icon images
├── public/                 # Dashboard SPA (served by FastAPI)
│   ├── index.html          # Main HTML shell (865 lines)
│   ├── app.js              # Full SPA logic — vanilla JS (9,982 lines)
│   ├── css/shell.css       # Dashboard styles (849 lines)
│   ├── js/monitor.js       # Live monitoring panel (88 lines)
│   ├── js/parent-filter.js # Parent card filtering (243 lines)
│   ├── assets/data/        # Bundled character data for UI
│   ├── item_icons/         # Item icon images
│   └── races/              # Race images (PNG)
├── scripts/                # Offline tooling and analysis scripts
│   ├── backtest_training_scorer.py  # Backtest scorer against historical logs (450 lines)
│   ├── benchmark.py        # Career benchmark runner (615 lines)
│   ├── generate_master_data.py      # Standalone master.mdb data generation (36 lines)
│   └── promote_policy.py   # Promote learned policy adjustments (223 lines)
├── tests/                  # Test suite (90+ test files)
│   └── test_*.py           # Pytest test modules
├── uma_runtime/            # Runtime output (gitignored except structure)
│   └── <profile>/          # Per-profile runtime directory
│       ├── bot_logs/       # Career run JSON reports
│       ├── ai/             # AI datasets, models, advisor stats
│       │   ├── llm_advisor/ # Local LLM advice outputs
│       │   └── post_run_reports/ # Post-run analysis reports
│       ├── decision_traces/ # Turn-by-turn decision trace logs
│       ├── state_snapshots/ # Game state snapshots
│       └── discord_telemetry/ # Discord telemetry JSONL
├── docs/                   # Design documents and feature specs
│   ├── *.md                # ~50 feature design docs
│   └── archive/            # Archived/superseded design docs
└── .planning/              # GSD planning documents
    └── codebase/           # Codebase analysis (this file)
```

## Directory Purposes

**`career_bot/`:**
- Purpose: Core domain logic for career automation
- Contains: Strategy implementations, scoring algorithms, data loaders, AI analytics, telemetry
- Key files: `runner.py` (execution engine), `scenarios/mant.py` (decision logic), `trackblazer.py` (race solver)

**`career_bot/scenarios/`:**
- Purpose: Scenario-specific strategy implementations
- Contains: `base.py` (ABC + Decision dataclass), `mant.py` (Scenario 4), `mant_trackblazer.py` (Trackblazer-aware extension)
- Key pattern: Strategy pattern with `ScenarioStrategy.next_decision(state, preset) -> Decision`

**`uma_api/`:**
- Purpose: Encrypted game server communication
- Contains: API client with AES-CBC + msgpack, Steam ticket generation (embedded Node.js), career recovery
- Key files: `client.py` (UmaClient class), `career_recovery.py` (102 error handler)

**`data/`:**
- Purpose: Static game data catalogs, user presets, character metadata
- Contains: 52+ JSON files, character images, skill icons, race images
- Key files: `event_outcomes.json`, `race_map.json`, `chara_list.json`, `support_list.json`, `skill_data.json`, `master_table_catalog_core.json`

**`data/character_data/`:**
- Purpose: Community-maintained character presets and epithet catalog
- Contains: `character_presets.json` (59 trainees with aptitudes), `epithets.json` (217 epithets)

**`data/character_profiles/`:**
- Purpose: Per-character profile definitions with aptitudes and style preferences
- Contains: Individual `<name>.json` files + `index.json`

**`data/presets/`:**
- Purpose: Default career presets shipped with the build
- Contains: JSON preset files (migrated to userdata dir on first run)

**`data/trackblazer/`:**
- Purpose: Smart race solver reference data
- Contains: `races.json`, `epithets.json`, `debut_races.json`, `race_agendas.json`

**`public/`:**
- Purpose: Dashboard single-page application served by FastAPI
- Contains: HTML, JS, CSS, and static assets (images/icons)
- Key files: `app.js` (9,982 lines of vanilla JS SPA logic), `index.html` (shell with theme/loading)

**`scripts/`:**
- Purpose: Offline development/analysis tools
- Contains: Backtesting, benchmarking, master data generation, policy promotion
- Key files: `benchmark.py` (career benchmark harness), `backtest_training_scorer.py` (scorer validation)

**`tests/`:**
- Purpose: Pytest test suite
- Contains: 90+ test files covering sprints, features, and regression tests
- Key pattern: Files named `test_sweepymodv{N}_{feature}.py` for sprint-based feature tests

**`uma_runtime/`:**
- Purpose: Runtime output directory for logs, AI data, and diagnostics
- Contains: Per-profile subdirectories with bot_logs, ai exports, decision traces, state snapshots
- Generated: Yes (created at runtime)
- Committed: Directory structure only (contents gitignored)

**`docs/`:**
- Purpose: Feature design documents and specifications
- Contains: ~50 markdown files documenting feature designs across versions
- Generated: No (hand-written design docs)

## Key File Locations

**Entry Points:**
- `main.py`: Primary application entry -- FastAPI server
- `manager.py`: Multi-instance supervisor
- `run.bat`: Windows one-click launcher

**Configuration:**
- `settings.json`: Default application settings (turn delay, TP recovery)
- `data/active_preset.json`: Last-used preset reference
- `data/settings_presets.json`: Saved settings presets
- `data/skill_config.json`: Skill purchase configuration

**Core Logic:**
- `career_bot/runner.py`: Career execution engine (CareerRunner)
- `career_bot/scenarios/mant.py`: Primary scenario strategy (MantStrategy)
- `career_bot/training_scorer.py`: Training command scorer (TrainingScorerConfig, score_trainings)
- `career_bot/trackblazer.py`: Smart race solver (solve_local)
- `uma_api/client.py`: Game server API client (UmaClient)

**AI/Analytics:**
- `career_bot/ai_dataset.py`: JSONL export (turn_decisions, event_outcomes, career_summaries)
- `career_bot/ai_advisor.py`: Race program advisor (Beta-Binomial posterior)
- `career_bot/ai_trainer.py`: Background model training + policy hints
- `career_bot/ai_modeling.py`: Bayesian primitives (BetaPosterior, hierarchical_posterior)

**Testing:**
- `tests/test_*.py`: All test modules (90+ files)

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `training_scorer.py`, `career_recovery.py`)
- Test files: `test_{feature_or_version}.py` (e.g., `test_sweepymodv544_event_outcomes.py`)
- JSON data: `snake_case.json` or `snake_case_core.json` for master.mdb-derived tables
- Sprint-based test naming: `test_sweepymodv{sprint_number}_{feature}.py`

**Directories:**
- Package dirs: `snake_case` (e.g., `career_bot`, `uma_api`)
- Data subdirs: `snake_case` (e.g., `character_data`, `skill_icons`)
- Runtime output: `snake_case` (e.g., `bot_logs`, `decision_traces`)

**Classes:**
- PascalCase: `CareerRunner`, `MantStrategy`, `UmaClient`, `ConfigStore`, `TrainingScorerConfig`

**Functions:**
- snake_case: `next_decision()`, `score_trainings()`, `load_race_agendas()`
- Private: underscore prefix: `_resolve_userdata_dir()`, `_read_settings()`

**Constants:**
- UPPER_SNAKE_CASE: `SPEED_PRESETS`, `BASE_URL`, `TRAINING_LABELS`, `STAT_KEYS`

**API Routes:**
- Pattern: `/api/{resource}/{action}` with kebab-case (e.g., `/api/career/run`, `/api/settings/turn-delay`, `/api/ai/auto-training/config`)

## Import Organization

**Order observed in career_bot modules:**
1. Standard library (`json`, `os`, `threading`, `time`, `math`, `pathlib`)
2. Third-party (rare -- most deps are in `main.py` and `uma_api/client.py`)
3. Internal `career_bot.*` imports (relative or absolute)

**Path aliases:** None. All imports use absolute package paths (`from career_bot.events import EventManager`).

## Where to Add New Code

**New Scenario Strategy:**
- Create: `career_bot/scenarios/{name}.py`
- Extend: `ScenarioStrategy` base class from `career_bot/scenarios/base.py`
- Register: Add to `STRATEGIES` dict in `career_bot/runner.py:30`
- Tests: `tests/test_{name}_scenario.py`

**New API Endpoint:**
- Add route in `main.py` using `@app.get()` / `@app.post()` decorator
- Follow existing pattern: route handler calls domain logic from `career_bot/`
- Place near related endpoints (routes are grouped by feature area in `main.py`)

**New Career Bot Module:**
- Create: `career_bot/{module_name}.py`
- Import from `main.py` or from other `career_bot/` modules
- Follow pattern: module provides functions/classes, `main.py` wires them to routes
- Tests: `tests/test_{module_name}.py`

**New Data File:**
- Static game data: `data/{name}.json` (suffix `_core.json` if derived from master.mdb)
- Character profiles: `data/character_profiles/{name}.json`
- Trackblazer data: `data/trackblazer/{name}.json`

**New Dashboard Feature:**
- UI logic: Add to `public/app.js` (single vanilla JS file, no build step)
- Styles: Add to `public/css/shell.css`
- New JS module: `public/js/{name}.js` (loaded by index.html)

**New Test:**
- Create: `tests/test_{feature_name}.py`
- Convention: Sprint-based naming `test_sweepymodv{N}_{feature}.py` for feature tests
- Pattern: Import from `career_bot.*` directly (never import `main.py`)

**New Script:**
- Create: `scripts/{name}.py`
- Purpose: Offline analysis, data generation, or tooling
- Pattern: Standalone executable, imports from `career_bot.*`

## Special Directories

**`uma_runtime/`:**
- Purpose: All runtime-generated outputs (logs, AI data, diagnostics, snapshots)
- Generated: Yes (created by `main.py` and `career_bot/runner.py`)
- Committed: No (gitignored)
- Resolved via: `runtime_output_root()` function (checks `UMA_RUNTIME_DIR` env, then `.git`-relative, then sibling)

**`USERDATA_DIR` (external):**
- Purpose: User configuration that persists across version upgrades (presets, settings, auth, accounts)
- Generated: Yes (populated by migration on first run)
- Committed: No (lives outside the build directory)
- Resolved via: `_resolve_userdata_dir()` in `main.py:260` (env vars -> `~/.icarus/userdata_pointer.json` -> sibling folder -> build dir fallback)

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (by `run.bat` or manual `uv venv`)
- Committed: No (gitignored)

**`node_modules/`:**
- Purpose: Node.js dependencies (steam-user for Steam ticket generation)
- Generated: Yes (by `npm install`)
- Committed: No (gitignored)

---

*Structure analysis: 2026-06-27*
