# Technology Stack

**Analysis Date:** 2026-06-27

## Languages

**Primary:**
- Python 3.13 (preferred; `run.bat` creates venv with `--python 3.13`) - All backend logic, API server, career bot, AI modules
- JavaScript (vanilla ES6+) - Frontend dashboard (`public/app.js`, `public/js/monitor.js`, `public/js/parent-filter.js`), inline Frida injection script in `main.py`

**Secondary:**
- HTML/CSS - Single-page dashboard (`public/index.html`, `public/styles.css`, `public/css/shell.css`)
- Batch script - Windows launcher (`run.bat`)

## Runtime

**Environment:**
- CPython 3.13+ (bootstrapped via `uv venv` or `python -m venv` in `run.bat`)
- Node.js (LTS) - Required at runtime for Steam authentication ticket generation via `steam-user` npm package; invoked as a subprocess from `uma_api/client.py`

**Package Manager:**
- pip / uv - Python dependencies (`requirements.txt`); `run.bat` prefers `uv pip install`
- npm - Node.js dependency (`package.json` declares single dependency `steam-user`)
- Lockfile: `package-lock.json` present for npm; no Python lockfile (pip freeze not committed)

## Frameworks

**Core:**
- FastAPI 0.136.1 - HTTP API server hosting ~141 REST endpoints, static file serving for dashboard (`main.py`)
- Pydantic 2.13.4 - Request/response model validation for FastAPI endpoints (`main.py`)
- uvicorn 0.18.2 - ASGI server running FastAPI app on `127.0.0.1:{PORT}` (`main.py:7787`)

**Instrumentation:**
- Frida 17.9.1 - Dynamic instrumentation framework; attaches to `UmamusumePrettyDerby.exe` process to intercept TLS traffic and capture authentication credentials (`main.py:7707`, `JS_CODE` block at `main.py:61-206`)

**Testing:**
- pytest (implied by `tests/` directory with `test_*.py` naming convention) - No explicit test framework in `requirements.txt`; tests use plain `assert` statements

**Build/Dev:**
- No build tooling for frontend (vanilla JS/CSS, no bundler)
- `run.bat` - Windows one-click launcher that creates venv, installs deps, starts server

## Key Dependencies

**Critical (requirements.txt):**
- `frida==17.9.1` - Game process instrumentation for auth credential capture
- `curl_cffi==0.7.4` - HTTP client with browser TLS fingerprint impersonation; used by `UmaClient` for all game API calls (`uma_api/client.py:6`)
- `msgpack==1.1.0` - Binary serialization matching the game's wire protocol (`uma_api/client.py`)
- `pycryptodome==3.14.1` - AES-CBC encryption/decryption of game API request/response payloads (`uma_api/client.py:11-12`)
- `requests==2.33.1` - Standard HTTP client used by `local_llm.py` for OpenAI-compatible API calls and general HTTP operations
- `scipy>=1.11` - Beta-Binomial posterior modeling for AI advisor race outcome predictions (`career_bot/ai_modeling.py`)

**Infrastructure (npm via package.json):**
- `steam-user@^5.0.0` - Steam client library for generating auth session tickets; executed as Node.js subprocess (`uma_api/client.py:48-116`)

## Configuration

**Environment Variables (never read .env files directly; no dotenv):**
- `ICARUS_USERDATA_DIR` / `SWEEPYCL_USERDATA_DIR` / `SWEEPYCLAUDE_USERDATA_DIR` - Override userdata folder location
- `UMA_RUNTIME_DIR` - Override runtime output directory
- `UMA_DISCORD_WEBHOOK_URL` - Discord webhook URL for telemetry
- `UMA_DISCORD_LOGGING` - Enable/disable Discord telemetry (`1`/`true`/`yes`/`on`)
- `UMA_STUCK_TURN_THRESHOLD` - Turn stall detection threshold
- `SWEEPY_AUTH_CAPTURE_TIMEOUT_SEC` - Frida auth capture timeout (default 180s)

**JSON Configuration Files:**
- `settings.json` - Root settings file (turn delays, TP recovery mode)
- `data/discord_logging.json` / `data/discord_logging.example.json` - Discord webhook config
- `data/skill_config.json` - Skill buying strategy configuration
- `data/smart_solver_config.json` - Smart race solver settings
- `data/settings_presets.json` - Named settings profiles
- `accounts.json` - Multi-instance account roster (used by `manager.py`)

**User Data Resolution (priority order, `main.py:260-343`):**
1. `$ICARUS_USERDATA_DIR` env var
2. `$SWEEPYCL_USERDATA_DIR` env var (legacy)
3. `~/.icarus/userdata_pointer.json` cross-version pointer
4. `../Icarus_userdata/` sibling folder
5. Build directory fallback

**Build/Runtime Generated:**
- `uma_runtime/` - Runtime output directory (traces, AI datasets, logs, manager status); gitignored
- `career_bot/.timing_dna` - Per-install random seed for humanized timing; gitignored

## Data Layer

**Static Game Data (committed, `data/` directory):**
- 50+ JSON files containing game master data extracts (race maps, skill data, character profiles, support cards, scenario configuration)
- Sourced from game's `master.mdb` SQLite database via `scripts/generate_master_data.py` -> `career_bot/master_data.py`
- Pattern: `*_core.json` files are generated from master database; other JSON files are hand-curated or scraped

**Runtime Data (gitignored, `uma_runtime/`):**
- API trace logs (`uma_runtime/trace_logs/api_payloads/`)
- AI training datasets (`uma_runtime/ai/`)
- Career reports and telemetry JSONL
- Manager status (`uma_runtime/manager_status.json`)
- Discord telemetry JSONL (`uma_runtime/discord_telemetry/`)

**No Traditional Database:**
- All persistent state is JSON files on disk
- SQLite is read-only: the game's `master.mdb` is read during data generation (`career_bot/master_data.py`), never written to
- Game state lives server-side; the bot only caches it locally in memory and JSON

## Platform Requirements

**Development:**
- Windows 11 (hard requirement: `uma_api/client.py` uses `winreg` for GPU/HWID/device info)
- Python 3.13+
- Node.js LTS (for Steam auth)
- Umamusume Pretty Derby PC (Steam) installed

**Production (same machine):**
- Windows-only deployment (runs locally alongside the game)
- Frida requires the game process to be running for auth capture
- Dashboard served on localhost (`127.0.0.1:{PORT}`, default 1616)
- Multi-instance support via `manager.py` (each instance gets its own port)

---

*Stack analysis: 2026-06-27*
