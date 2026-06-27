# External Integrations

**Analysis Date:** 2026-06-27

## APIs & External Services

**Umamusume Game Server API:**
- Base URL: `https://api.games.umamusume.com/umamusume/`
- SDK/Client: Custom `UmaClient` class in `uma_api/client.py`
- Auth: AES-CBC encrypted msgpack payloads; credentials captured via Frida from running game process
- Wire Protocol: Base64-encoded, AES-CBC encrypted msgpack with MD5-based session ID chaining
- Key endpoints used:
  - `tool/start_session` - Session initialization
  - `tool/signup`, `tool/pre_signup` - Account registration
  - `load/index` - Account data loading
  - `single_mode_free/*` - Career mode operations (start, load, exec_command, check_event, race_entry/start/end/out, gain_skills, multi_item_use, multi_item_exchange, finish, reserve_race, change_running_style, continue, minigame_end)
  - `pre_single_mode/index` - Pre-career setup
  - `user/recovery_trainer_point` - TP recovery with jewels
  - `item/use_recovery_item` - TP recovery with items
  - `trained_chara/remove` - Delete trained characters
  - `read_info/index` - Account info refresh
- Rate limiting: Built-in `MIN_CALL_SPACING` (0.14s default), humanized delays via `career_bot/delay.py`
- Error handling: Automatic retry for codes 205 (transient), 208 (server busy), 394 (expired ticket), 709 (viewer ID mismatch); HTTP 5xx retries with exponential backoff (`uma_api/client.py:597-765`)
- Anti-detection: Humanized timing with per-install random seed (`career_bot/delay.py`), simulated button click coordinates for race_out (`uma_api/client.py:614-643`), browser-like TLS fingerprinting via `curl_cffi`

**Steam Platform:**
- Purpose: Authentication ticket generation for game server login
- SDK/Client: `steam-user` npm package executed as Node.js subprocess (`uma_api/client.py:48-116, 326-358`)
- Auth: Steam username + password passed as CLI args to inline JS script; supports Steam Guard 2FA codes
- Flow: `get_ticket()` -> spawns `node -e TICKET_GEN_JS` -> returns `(steam_id, session_ticket)` hex
- Error codes: Exit code 2 = `STEAM_GUARD_REQUIRED` (needs 2FA); other = credential error
- Mid-run refresh: `UmaClient.refresh_steam_ticket()` mints fresh ticket when server reports 394 (`uma_api/client.py:817-837`)
- Dependencies: Requires `node` and `npm` on PATH; auto-installs `node_modules` if missing (`uma_api/client.py:300-323`)

**Local LLM (Optional):**
- Purpose: Post-run analysis and shadow turn advice (advisory only, never executes actions)
- SDK/Client: OpenAI-compatible chat completions API via `requests.post` (`career_bot/local_llm.py`)
- Supported providers: LM Studio (`http://localhost:1234/v1`), Ollama, or any OpenAI-compatible server
- Auth: Bearer token via `api_key` config field (default `"lm-studio"`)
- Endpoint: `{base_url}/chat/completions`
- Config: `uma_runtime/ai/local_llm_config.json`
- Modes: `off`, `offline` (post-run only), `shadow` (live advisory), `recommend` (shadow + recommendations)
- Context budget: 12,000 chars; auto-trims turn data to fit local 4k/8k context windows
- Files written: `llm_advice.jsonl`, `llm_run_summaries.jsonl`, `latest_llm_advice.json`, `latest_llm_run_summary.json`

## Data Storage

**Databases:**
- SQLite (read-only, external) - Game's `master.mdb` database
  - Connection: User-supplied path via dashboard or `--db-path` CLI arg; auto-detected from Steam install path
  - Client: Python `sqlite3` stdlib module (`career_bot/master_data.py:2270`)
  - Purpose: Extract game reference data (skills, races, cards, scenarios, etc.) into JSON files under `data/`
  - 60+ tables read including `skill_data`, `race`, `card_data`, `chara_data`, `support_card_data`, `single_mode_*` tables
  - Never written to; read-only extraction to `data/*_core.json` files

**File Storage:**
- Local filesystem only
  - `data/` - Committed static game data JSONs
  - `data/presets/` - User-created training presets (JSON)
  - `data/character_profiles/` - Character-specific configuration JSONs
  - `data/character_data/` - Character aptitude and stat data JSONs
  - `uma_runtime/` - All runtime output (gitignored)
  - `uma_runtime/ai/` - AI training datasets, models, and LLM artifacts (JSONL + JSON)
  - `uma_runtime/trace_logs/api_payloads/` - API request/response trace logs (JSONL)
  - `uma_runtime/discord_telemetry/` - Local copies of Discord telemetry (JSONL)
  - `uma_runtime/manager_logs/` - Multi-instance manager log files
  - Userdata folder (configurable, may be external to build dir) - Settings, presets, accounts, auth configs

**Caching:**
- In-memory only via `UmaClient` instance attributes (`cached_load_data`, `tp_info`, `coin_info`, `item_map`)
- No external cache service (Redis, Memcached, etc.)

## Authentication & Identity

**Auth Provider: Steam (custom integration)**
- Implementation: Steam session ticket generated via `steam-user` npm library -> presented to game server
- Credential storage:
  - `{userdata}/auth/{profile_name}/auth_config.json` - Obfuscated auth credentials (viewer_id, udid, auth_key, steam_id, steam_session_ticket)
  - `{userdata}/auth/{profile_name}/steam_token.txt` - Steam token persistence
  - Written to both runtime build folder and userdata folder for cross-version survival (`main.py:389-406`)
- Frida-based capture: When no saved credentials exist, attaches to running game process via Frida to intercept TLS traffic and extract viewer_id, udid, auth_key from encrypted API payloads (`main.py:7680-7740`)
- Session management: MD5-based session ID chain (`make_sid()` -> `next_sid()` after each API call) (`uma_api/client.py:169-173`)
- Multi-account: `accounts.json` roster with per-account auth profiles; `manager.py` launches separate `main.py` instances per account

## Monitoring & Observability

**Error Tracking:**
- Console print statements throughout (no structured error tracking service)
- API errors logged to trace JSONL files (`uma_api/client.py:418-444`)
- Career error state captured in report JSON (`career_bot/report.py`)

**Logs:**
- API trace logs: JSONL files per session in `uma_runtime/trace_logs/api_payloads/` - every request/response logged with timestamps and request IDs
- Career reports: JSON per career run in `uma_runtime/career_reports/`
- Manager logs: Per-instance log files in `uma_runtime/manager_logs/`
- AI training data: JSONL datasets in `uma_runtime/ai/`
- Console output: `print()` statements (no logging framework)
- Health endpoint: `/api/health` exposes runner state, stale seconds, diagnostics

**Dashboard:**
- Web UI served at `http://127.0.0.1:{PORT}` (default 1616)
- ~141 REST API endpoints for monitoring, configuration, and control
- Auto-opens in default browser on launch (`main.py:7786`)

## CI/CD & Deployment

**Hosting:**
- Local Windows desktop application only
- No cloud deployment; runs alongside game on same machine
- Multi-instance via `manager.py` which spawns and supervises child `main.py` processes

**CI Pipeline:**
- None detected (no `.github/workflows/`, no CI config files)

## Webhooks & Callbacks

**Outgoing - Discord Webhooks:**
- Purpose: Career telemetry export (turn logs and career summaries)
- Implementation: `career_bot/discord_logger.py` - `DiscordCareerLogger` class
- Config: `data/discord_logging.json` or `UMA_DISCORD_WEBHOOK_URL` env var
- Features:
  - Batched sending (configurable batch size and flush interval)
  - Automatic sensitive data redaction (Steam tickets, viewer IDs, device info, auth keys)
  - Rate limit handling (respects Discord 429 responses with `retry_after`)
  - Small payloads sent as code blocks; large payloads sent as JSONL file attachments
  - Local JSONL copy always written to `uma_runtime/discord_telemetry/` even when webhook disabled
- Payload types: `career_start`, `turn`, `career_summary`

**Incoming:**
- None (the FastAPI server only serves the local dashboard; no external webhook receivers)

## Environment Configuration

**Required for operation:**
- Windows OS (hard requirement for `winreg` GPU/HWID detection)
- Node.js on PATH (for Steam auth)
- Game installed (Steam app ID 3224770)
- Steam credentials (username + password, optionally 2FA code)

**Optional env vars (listed in STACK.md):**
- `ICARUS_USERDATA_DIR` - Userdata folder override
- `UMA_RUNTIME_DIR` - Runtime output override
- `UMA_DISCORD_WEBHOOK_URL` - Discord webhook
- `UMA_DISCORD_LOGGING` - Discord telemetry toggle
- `UMA_STUCK_TURN_THRESHOLD` - Stall detection
- `SWEEPY_AUTH_CAPTURE_TIMEOUT_SEC` - Auth capture timeout

**Secrets location:**
- `.env` file existence noted (never read by code; no dotenv usage)
- Auth credentials in `{userdata}/auth/{profile}/auth_config.json` (obfuscated)
- Steam credentials entered via dashboard UI at runtime (not persisted in plaintext)
- Discord webhook URL in `data/discord_logging.json` or env var

## Game Process Integration

**Frida Instrumentation (`main.py:61-206, 7680-7740`):**
- Attaches to `UmamusumePrettyDerby.exe` Windows process
- Hooks `il2cpp_unity_install_unitytls_interface` to intercept Unity TLS layer
- Intercepts outgoing HTTPS POST requests to `/umamusume/` endpoints
- Parses wire protocol to extract viewer_id, udid, auth_key, app_ver, res_ver
- One-time capture: runs during initial setup when no saved auth exists
- Sends captured credentials back to Python via Frida message handler

**Steam Game Launch (`main.py`):**
- Can launch game via Steam protocol URL (`steam://rungameid/3224770`)
- Waits for process to appear, then attaches Frida

---

*Integration audit: 2026-06-27*
