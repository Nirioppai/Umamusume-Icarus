<!-- refreshed: 2026-06-27 -->
# Architecture

**Analysis Date:** 2026-06-27

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                   Web Dashboard (Browser)                    │
│              `public/index.html` + `public/app.js`           │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP (fetch → /api/*)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Server  (`main.py`)                    │
│   7,787 lines — routes, auth, state, Frida injection,       │
│   career orchestration, static file serving                  │
├──────────────┬──────────────┬───────────────────────────────┤
│  CareerRunner│  ConfigStore │  UmaClient                    │
│ `career_bot/ │ `career_bot/ │ `uma_api/                     │
│  runner.py`  │  config_     │  client.py`                   │
│              │  store.py`   │                               │
└──────┬───────┴──────┬───────┴──────────┬────────────────────┘
       │              │                  │
       ▼              ▼                  ▼
┌──────────────┐ ┌──────────┐ ┌──────────────────────────────┐
│ Strategy     │ │  JSON    │ │ Umamusume Game API           │
│ Engine       │ │  Data    │ │ api.games.umamusume.com      │
│ `career_bot/ │ │ `data/`  │ │ (AES-encrypted msgpack)      │
│  scenarios/` │ │          │ └──────────────────────────────┘
│ + Trackblazer│ │          │
│ + AI Layer   │ │          │
└──────┬───────┘ └──────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│          Runtime Output  (`uma_runtime/<profile>/`)          │
│  bot_logs/ | ai/ | decision_traces/ | state_snapshots/       │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI server | HTTP API, static files, auth, session state, career orchestration | `main.py` |
| Manager | Multi-instance supervisor with health checks and auto-restart | `manager.py` |
| CareerRunner | Threaded career execution loop (train/race/event per turn) | `career_bot/runner.py` |
| MantStrategy | Turn-by-turn decision logic for Scenario 4 (Mant/Training) | `career_bot/scenarios/mant.py` |
| ScenarioStrategy | Abstract base class for scenario strategies | `career_bot/scenarios/base.py` |
| UmaClient | Encrypted API transport (AES+msgpack) to game servers | `uma_api/client.py` |
| CareerRecovery | Resume in-progress careers after result_code 102 | `uma_api/career_recovery.py` |
| RacePlanner | Race schedule solver (heuristic + MILP) with live replanning | `career_bot/races.py` |
| SkillBuyer | Skill purchase strategy with profile-aware scoring | `career_bot/skills.py` |
| MantItemManager | In-career item shop management (buy/use consumables) | `career_bot/items.py` |
| EventManager | Event choice resolution from outcome KB + scraped effects | `career_bot/events.py` |
| TrainingScorer | Heuristic scorer for training command selection | `career_bot/training_scorer.py` |
| ConfigStore | Preset CRUD (settings presets, skill configs, solver configs) | `career_bot/config_store.py` |
| Trackblazer | Smart race solver — epithet-aware schedule optimization | `career_bot/trackblazer.py` |
| MasterData | SQLite reader for game's master.mdb (skill/race/card tables) | `career_bot/master_data.py` |
| AI Dataset | JSONL export of career turn/event/outcome data for analytics | `career_bot/ai_dataset.py` |
| AI Advisor | Beta-Binomial race outcome scoring from historical data | `career_bot/ai_advisor.py` |
| AI Trainer | Background model builder (analytics, policy hints, reports) | `career_bot/ai_trainer.py` |
| Local LLM | Optional local LLM adapter for post-run analysis | `career_bot/local_llm.py` |
| DiscordLogger | Webhook telemetry for career logs | `career_bot/discord_logger.py` |
| PolicyGuards | Safety rails on learned policy adjustments (KL drift detection) | `career_bot/policy_guards.py` |
| Delay/DNA | Human-like timing delays with per-instance DNA seed | `career_bot/delay.py` |
| Dashboard UI | Single-page vanilla JS application | `public/app.js` |

## Pattern Overview

**Overall:** Monolithic single-process server with embedded game automation engine

**Key Characteristics:**
- Single `main.py` (7,787 lines) acts as the application shell: FastAPI routes, module-level global state, auth flow, Frida injection JS, career orchestration
- `career_bot/` package provides the domain logic as pure-ish modules imported by `main.py`
- `uma_api/` package handles encrypted game protocol transport
- No ORM, no database for app state -- JSON files for persistence, module-level globals for session state
- Multi-instance support via `manager.py` supervisor spawning child `main.py` processes

## Layers

**Presentation Layer (Dashboard):**
- Purpose: Browser-based SPA for login, career setup, monitoring, configuration
- Location: `public/`
- Contains: `index.html` (865 lines), `app.js` (9,982 lines), `css/shell.css`, `js/monitor.js`, `js/parent-filter.js`
- Depends on: FastAPI `/api/*` endpoints
- Used by: End users via browser at `http://127.0.0.1:{PORT}`

**API Layer (FastAPI):**
- Purpose: REST endpoints (~130 routes), static file serving, session management
- Location: `main.py`
- Contains: Route handlers, request/response models, global session state, auth/login flow, Frida credential injection
- Depends on: `career_bot/*`, `uma_api/*`
- Used by: Dashboard UI, manager health checks

**Domain Logic (Career Bot):**
- Purpose: Game automation decision engine -- training, racing, skills, events, items
- Location: `career_bot/`
- Contains: Strategy pattern for scenarios, scoring algorithms, race planning, skill purchasing, event handling
- Depends on: `data/*.json` files, `uma_api/client.py`
- Used by: `main.py` routes and `CareerRunner`

**Transport Layer (UMA API):**
- Purpose: Encrypted communication with Umamusume game servers
- Location: `uma_api/`
- Contains: AES-CBC encryption, msgpack serialization, Steam ticket generation (Node.js subprocess), career recovery
- Depends on: `curl_cffi`, `pycryptodome`, `msgpack`, Node.js `steam-user` package
- Used by: `main.py` (login), `career_bot/runner.py` (career actions)

**Data Layer:**
- Purpose: Static game data, user configuration, runtime outputs
- Location: `data/` (static), `uma_runtime/` (runtime), `USERDATA_DIR` (persistent user config)
- Contains: JSON catalogs (52+ files), character images, race images, item icons, presets
- Depends on: `master.mdb` (SQLite, game's master database)
- Used by: All career_bot modules

## Data Flow

### Primary Career Run Path

1. User clicks "Run" in dashboard (`public/app.js` sends POST `/api/career/run`)
2. `main.py:run_career()` validates preset, loads/resumes career via UmaClient (`main.py:5478`)
3. `CareerRunner.start()` spawns a background thread (`career_bot/runner.py:60`)
4. Each turn: runner calls `MantStrategy.next_decision(state, preset)` (`career_bot/scenarios/mant.py:44`)
5. Strategy evaluates training scores, events, race schedule, items, energy (`career_bot/scenarios/mant.py`)
6. Decision is executed via `UmaClient.call(endpoint, payload)` (`uma_api/client.py`)
7. Turn report is appended; AI dataset export runs post-career (`career_bot/report.py`, `career_bot/ai_dataset.py`)

### Authentication Flow

1. On startup, `refresh_auth_before_serving()` checks saved `auth_config.json` (`main.py:7671`)
2. If saved auth valid: headless bypass -- no game launch needed (`main.py:7594`)
3. If no saved auth: launch game via Steam (`steam://rungameid/3224770`), attach Frida to intercept TLS (`main.py:62-205`)
4. Frida JS hooks `unitytls_write` to parse POST headers and extract `viewer_id`, `udid`, `auth_key` (`main.py:62-205`)
5. Captured credentials are AES-encrypted and persisted to `auth_config.json` in both runtime and userdata dirs

### Looping / Multi-Career Flow

1. User sets run count > 1 or infinite (run_count=0) in dashboard
2. `manage_career_loop()` runs in a daemon thread (`main.py:5384`)
3. After each career finishes: auto-start next, resume on 102 errors, handle TP recovery
4. Career history stored in-memory (`COMPLETED_CAREER_HISTORY`) and as JSON reports in `uma_runtime/bot_logs/`

### Smart Race Solver Flow

1. Dashboard sends POST `/api/trackblazer/plan` with trainee aptitudes and target epithets (`main.py:4453`)
2. `trackblazer.solve_local()` runs the local SmartRaceSolver port (`career_bot/trackblazer.py`)
3. Solver uses race data from `data/trackblazer/races.json`, `epithets.json`, `debut_races.json`
4. Live replanning happens mid-career when the runner detects schedule drift (`career_bot/races.py`)

**State Management:**
- Session state is module-level globals in `main.py`: `active_client`, `active_account`, `active_dashboard_data`, `active_selection`, `career_runner`
- User configuration persisted as JSON to `USERDATA_DIR` (resolved via env vars, pointer file, or sibling folder convention)
- Runtime artifacts written to `uma_runtime/<profile>/` (bot_logs, ai datasets, decision traces, state snapshots)
- No database -- all state is either in-memory globals or flat JSON files

## Key Abstractions

**Decision (dataclass):**
- Purpose: Represents a single turn decision (action + payload + reason)
- Examples: `career_bot/scenarios/base.py:5`
- Pattern: Strategy pattern -- `ScenarioStrategy.next_decision()` returns a `Decision`

**UmaClient:**
- Purpose: Authenticated encrypted API client for game server
- Examples: `uma_api/client.py`
- Pattern: Stateful client with AES-CBC encryption, msgpack serialization, session ID chaining

**ConfigStore:**
- Purpose: CRUD for user presets across three config planes (settings, skills, solver)
- Examples: `career_bot/config_store.py`
- Pattern: File-backed store with hydration/serialization, migration from legacy formats

**CareerRunner:**
- Purpose: Threaded career execution engine with pause/stop/loop controls
- Examples: `career_bot/runner.py:60`
- Pattern: Background thread with lock-protected status dict, polling-based dashboard updates

## Entry Points

**`main.py` (primary):**
- Location: `main.py:7744`
- Triggers: `python main.py [config.json]` or `run.bat`
- Responsibilities: Start FastAPI server on `127.0.0.1:{PORT}`, auto-open browser, refresh auth, start background AI trainer

**`manager.py` (multi-instance):**
- Location: `manager.py:200`
- Triggers: `python manager.py`
- Responsibilities: Read `accounts.json`, spawn child `main.py` processes, health-check loop, auto-restart on crash/stale

**`run.bat` (Windows launcher):**
- Location: `run.bat`
- Triggers: Double-click on Windows
- Responsibilities: Create venv, install deps via `uv pip`, run `main.py`

## Architectural Constraints

- **Threading:** Single-threaded FastAPI event loop for HTTP, with a dedicated background thread per career run (`CareerRunner.thread`). AI trainer, profile refresh, and discord logger also use daemon threads. No async career execution -- the runner is synchronous in its own thread.
- **Global state:** Extensive module-level mutable globals in `main.py` (~20 globals including `active_client`, `active_account`, `career_runner`, `preset_store`, `speed_level`, `api_delay_scale`). These are NOT thread-safe in general; `CareerRunner` uses its own `threading.Lock`.
- **Circular imports:** None observed -- `main.py` imports from `career_bot.*` and `uma_api.*`; those packages do not import `main`. Some `career_bot` modules have guarded try/except imports for optional cross-module features.
- **Single-instance limitation:** Each `main.py` process handles exactly one logged-in game account. Multi-account requires the `manager.py` supervisor spawning separate processes on different ports.
- **Monolithic main.py:** At 7,787 lines, `main.py` combines API routing, auth, state management, Frida JS injection code, and career orchestration in a single file. This is the dominant architectural constraint.

## Anti-Patterns

### God Module

**What happens:** `main.py` (7,787 lines) contains API routes, authentication logic, Frida injection JavaScript, career orchestration, configuration management, static file serving, and ~20 module-level global variables.
**Why it's wrong:** Changes to any concern (auth, UI routing, career management) risk breaking unrelated functionality. The file cannot be imported in tests (circular state initialization).
**Do this instead:** Extract route groups into FastAPI routers in separate modules. Move auth to a dedicated module. Move Frida JS to a file. See `career_bot/` for the correct pattern of domain separation.

### Duplicated runtime_output_root()

**What happens:** The function `runtime_output_root()` is independently defined in `career_bot/runner.py`, `career_bot/ai_dataset.py`, `career_bot/race_intelligence.py`, `career_bot/diagnostics.py`, and `uma_api/client.py` -- each with slightly different implementations.
**Why it's wrong:** Five copies of the same path-resolution logic can drift apart, causing runtime artifacts to scatter across different directories.
**Do this instead:** Define once in a shared utility module (e.g., `career_bot/paths.py`) and import everywhere.

### Module-Level Side Effects

**What happens:** `main.py` executes substantial logic at import time: package validation, userdata resolution, config file loading, master.mdb generation, Frida JS compilation, preset store initialization.
**Why it's wrong:** Makes the module unimportable in test harnesses. Test files work around this by importing only `career_bot.*` submodules.
**Do this instead:** Gate initialization behind `if __name__ == "__main__"` or use FastAPI's lifespan hooks (partially done via `_lifespan`).

## Error Handling

**Strategy:** Defensive try/except with best-effort fallbacks. Errors in non-critical subsystems (AI, telemetry, profile refresh) are caught and logged but never block career execution.

**Patterns:**
- API errors from game server raise exceptions with `result_code` in message text; `career_recovery.py` pattern-matches on `"102"` to detect resumable careers
- `CareerRunner` catches exceptions per-turn and logs them to the report; consecutive failures trigger auto-stop
- UmaClient tracks `MIN_CALL_SPACING` and uses `dna_sleep()` for human-like timing to avoid detection
- JSON file writes use atomic tmp-then-replace pattern (`atomic_write_json()` in `manager.py`, similar patterns throughout)

## Cross-Cutting Concerns

**Logging:** `print()` to stdout/stderr with `flush=True`. No structured logging framework. Discord webhook logger (`career_bot/discord_logger.py`) provides optional telemetry export.

**Validation:** Pydantic `BaseModel` for API request validation. Internal data validation is ad-hoc with `isinstance` checks and safe_int/safe_float helpers.

**Authentication:** Steam session ticket-based auth. Credentials captured via Frida TLS interception or headless Node.js Steam login. Auth config persisted with base64 obfuscation (not encryption) to both runtime and userdata directories.

**Userdata Resolution:** Multi-strategy resolution in `_resolve_userdata_dir()` (`main.py:260`): env vars -> pointer file (`~/.icarus/userdata_pointer.json`) -> sibling folder convention -> build dir fallback. Ensures user config survives version upgrades.

---

*Architecture analysis: 2026-06-27*
