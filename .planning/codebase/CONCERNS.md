# Codebase Concerns

**Analysis Date:** 2026-06-27

## Tech Debt

**Monolithic `main.py` (7787 lines):**
- Issue: The entire FastAPI server, 141 API endpoints, 31+ Pydantic models, Frida JS injection code (~200 lines of inline JavaScript), auth handling, userdata management, timing/pacing engine, profile refresh scraper orchestration, and the career loop supervisor all live in a single file.
- Files: `main.py`
- Impact: Extremely difficult to navigate, test, or modify in isolation. Any change risks regressions in unrelated subsystems. New contributors face a steep learning curve. IDE indexing and autocompletion are slow.
- Fix approach: Extract into domain-focused modules:
  - `api/auth.py` — login, Steam ticket, Frida capture, headless bypass (~lines 400-700, 7500-7740)
  - `api/career.py` — career start/run/loop endpoints (~lines 4560-5600)
  - `api/settings.py` — settings, presets, delay, speed endpoints (~lines 880-1070, 2600-3000)
  - `api/setup.py` — setup/selection/deck/friend endpoints (~lines 5100-5500, 6500-7100)
  - `timing.py` — `wait_for_game_turn_delay`, `attach_turn_delay`, all pacing constants (~lines 1070-1260)
  - `frida_hook.py` — `JS_CODE` constant and `refresh_auth_before_serving` (~lines 61-205, 7660-7740)

**Pervasive module-level global state in `main.py`:**
- Issue: 30+ `global` declarations mutate shared variables (`active_client`, `active_account`, `active_dashboard_data`, `active_start_state`, `active_parent_cards`, `active_selection`, `pending_game_auth_config`, `raw_load_index_response`, `backend_loop_stop`, `_userdata_restart_pending`, `speed_level`, `api_delay_scale`, `turn_delay_*`, etc.) from async FastAPI handlers AND background threads. No synchronization protects most of these.
- Files: `main.py` (lines 600-612, 627, 892, 919, 1265, 2733, 4561, 4754, 4782, 5113, 5168, 5244, 5313, 5322, 5385, 5480, 5799, 6543, 6834, 6872, 6933, 6981, 7049, 7075, 7672)
- Impact: Race conditions between the FastAPI event loop (multiple concurrent async handlers), the career loop thread (`manage_career_loop`), the profile refresh thread, and the AI auto-trainer thread. A concurrent `/api/logout` + career loop iteration can null out `active_client` mid-call chain, causing `AttributeError`.
- Fix approach: Encapsulate mutable session state in a `SessionState` class protected by a `threading.Lock`. Pass the state object explicitly instead of relying on globals. `CareerRunner` already has a `self.lock` for its own status -- extend this pattern to the rest of the application state.

**Duplicate `import` statements in `main.py`:**
- Issue: Several stdlib modules are imported multiple times at different locations in the file: `import base64` (lines 3, 466), `import hashlib` (lines 485, 1069), `import uuid` (lines 486, 1070), `import random` (lines 41, 487, 1095), `import time` (lines 42, 1096). This is a symptom of the file growing organically without structural cleanup.
- Files: `main.py`
- Impact: Minor -- Python handles duplicate imports cleanly -- but it signals the file is too large for any developer to keep the full picture in mind.
- Fix approach: Consolidate all imports at the top of the file (or, better, split the file).

**Duplicate `runtime_output_root` implementations:**
- Issue: There are two separate implementations of `runtime_output_root()` -- one in `career_bot/runner.py` (lines 36-44, takes `base_dir` parameter) and one in `uma_api/client.py` (lines 34-43, takes no parameter, uses `__file__`). Both traverse parent directories looking for `.git`. They resolve to the same path but via different code paths, creating maintenance risk.
- Files: `career_bot/runner.py` (line 36), `uma_api/client.py` (line 34)
- Impact: If one is updated and the other is not, runtime paths diverge silently. The `uma_api/client.py` version runs at module import time and caches `TRACE_DIR` as a module-level constant.
- Fix approach: Create a single `runtime.py` module in the project root exporting `runtime_output_root(base_dir)` and have both consumers import it.

**Large `CareerRunner` class (4049 lines):**
- Issue: `career_bot/runner.py` contains a single `CareerRunner` class that handles the run loop, state management, action recording, metrics, decision tracing, factor extraction, scorer overrides, style adaptation, event capture, and more.
- Files: `career_bot/runner.py`
- Impact: Complex methods like `_extract_final_chara_payload` (lines 202-291) and `_apply_authoritative_scorer_override` (lines 3826-3960) are deeply nested in a class with 100+ methods. Testing individual behaviors requires mocking the entire runner.
- Fix approach: Extract pure-function helpers (factor extraction, scorer override logic, payload merging) into standalone modules that `CareerRunner` delegates to.

## Known Bugs

**Bare `except:` clause in `uma_api/client.py`:**
- Symptoms: A bare `except:` at line 357 catches all exceptions including `KeyboardInterrupt` and `SystemExit`, making the ticket generation process un-interruptible.
- Files: `uma_api/client.py` (line 357)
- Trigger: Any JSON parsing failure in `get_ticket()` output is caught with `except:` and re-raised as `Exception('bad json')`, masking the actual error.
- Workaround: The function is only called during initial auth, so it rarely hits this path in normal operation.

**Port-killing on startup can destroy unrelated processes:**
- Symptoms: `ensure_port_available()` in `main.py` (around line 7490) runs `taskkill /PID /F` on any process holding the configured port. If another application is legitimately using that port, it is killed without confirmation.
- Files: `main.py` (~line 7490-7514)
- Trigger: Start the bot when another service is bound to the same port (default 1616).
- Workaround: Use a non-colliding port via instance config.

## Security Considerations

**No CORS policy configured:**
- Risk: The FastAPI app binds to `127.0.0.1` (localhost only), which limits network exposure, but no CORSMiddleware is applied. A malicious web page open in the same browser could make cross-origin requests to the local server and exfiltrate session data, trigger career starts, or log the user out.
- Files: `main.py` (line 598, `app = FastAPI(lifespan=_lifespan)`)
- Current mitigation: Localhost-only binding. No remote access unless port-forwarded.
- Recommendations: Add `CORSMiddleware` restricting `allow_origins` to `["http://127.0.0.1:{PORT}"]`.

**Weak credential obfuscation (not encryption):**
- Risk: `_obfuscate_creds()` (line 469) uses base64 encoding of reversed strings (`"enc:" + b64(reversed_string)`). This is trivially reversible and provides no cryptographic protection. Auth config files (`auth_config.json`) containing Steam credentials are stored this way in both the runtime dir and userdata dir.
- Files: `main.py` (lines 469-481), auth config paths at `uma_runtime/{profile}/auth_config.json` and `{userdata}/auth/{profile}/auth_config.json`
- Current mitigation: `.gitignore` excludes `uma_runtime/`. The obfuscation deters casual glancing but not determined extraction.
- Recommendations: Use OS-level credential storage (Windows Credential Manager via `keyring` library) or at minimum AES encryption with a machine-specific key. Document that auth files contain sensitive credentials.

**Steam credentials passed via command-line arguments:**
- Risk: `get_ticket()` in `uma_api/client.py` (line 329) spawns a Node.js subprocess with `--username` and `--password` as CLI arguments. On Windows, these are visible in Task Manager and process listing tools to any user on the machine.
- Files: `uma_api/client.py` (line 329)
- Current mitigation: The ticket generation JS code is inlined (not a file on disk), limiting exposure window.
- Recommendations: Pass credentials via stdin to the subprocess or use environment variables.

**No authentication on the local API:**
- Risk: All 141 API endpoints are publicly accessible to any process on localhost without any authentication token, session cookie, or API key. Any local application or browser tab can call `/api/career/start`, `/api/logout`, or read session state.
- Files: `main.py` (all `@app.get` / `@app.post` routes)
- Current mitigation: Localhost-only binding.
- Recommendations: Add a session token generated on startup, passed as a header or query parameter. Store it in the served HTML/JS.

**Hardcoded cryptographic salt and header bytes:**
- Risk: `uma_api/client.py` (lines 118-119) contains hardcoded `SALT` and `HEAD` values used for API request packing. If the game server rotates these, the entire client breaks. These are also visible in the public repository.
- Files: `uma_api/client.py` (lines 118-119)
- Current mitigation: These mirror the game's own constants and are not user secrets.
- Recommendations: Move to a configuration file or environment variable so updates don't require code changes. Document that these are game protocol constants, not application secrets.

## Performance Bottlenecks

**Synchronous blocking in async FastAPI handlers:**
- Problem: Multiple `@app.post` handlers call `time.sleep()`, `active_client.call()` (synchronous HTTP to game server), and `start_career_from_request()` (which includes its own `time.sleep` calls and multiple API round-trips). These block the uvicorn event loop.
- Files: `main.py` -- 17 occurrences of `time.sleep` in the main file. `start_career_from_request()` (~line 4560) performs up to 23 sequential `active_client.call()` round-trips with interleaved `time.sleep(1)` calls for TP recovery.
- Cause: The handlers are defined as `async def` but execute synchronous blocking I/O directly instead of using `asyncio.to_thread()` or a thread pool.
- Improvement path: Move blocking operations to `asyncio.to_thread()`. The `_cached_poll` helper (line 5928) already demonstrates this pattern correctly -- extend it to all blocking handlers.

**Large JSON data files loaded synchronously at startup:**
- Problem: `data/master_table_catalog_core.json` (598KB), `data/event_effects_scraped.json` (1.2MB), `data/race_map.json` (360KB), and others are loaded and parsed on import. Total `data/` directory is 27MB.
- Files: `career_bot/events.py` (line 46), `career_bot/master_data.py`, multiple data loaders
- Cause: Each JSON file is loaded via `json.loads(path.read_text())` synchronously.
- Improvement path: Use lazy loading (load on first access) for non-critical data. Cache parsed data in memory after first load.

**Poll endpoints without TTL caching:**
- Problem: While `_cached_poll` exists for `diagnostics_summary` and `ai_status`, many other endpoints that return large payloads (career history, event choices, support card details) are computed fresh on every request.
- Files: `main.py` -- endpoints like `/api/career/history`, `/api/events/choices`, `/api/support-details`
- Cause: These endpoints were added incrementally without the caching pattern.
- Improvement path: Apply `_cached_poll` with appropriate TTLs to all heavy-read endpoints.

## Fragile Areas

**Timing / Anti-Detection Engine:**
- Files: `main.py` (lines 1069-1260), `career_bot/delay.py`
- Why fragile: The pacing system uses machine-specific hardware fingerprints (MAC address hash, screen resolution), per-session random jitter, per-endpoint log-normal distributions with fatigue cycles, and a secret "timing DNA" seed file (`career_bot/.timing_dna`). The logic spans two files with overlapping concerns -- `delay.py` provides base delay tables and `dna_sleep()`, while `main.py` adds its own `wait_for_game_turn_delay()` with endpoint-specific timing profiles. Modifying either without understanding both risks breaking the anti-detection properties.
- Safe modification: Always test timing changes with the "Safe" speed level. Log actual delays to verify distribution shape. Never modify `_T_M`, `_S_M`, `_C_P`, or `GLOBAL_SESSION_JITTER` without understanding their compound effect on the log-normal distribution.
- Test coverage: No tests verify timing distribution properties. The delay system is entirely untested.

**Auth Credential Lifecycle:**
- Files: `main.py` (lines 389-424, 7538-7656), `uma_api/client.py` (lines 360-415, 810-875)
- Why fragile: Credentials flow through 4+ code paths: (1) Frida capture -> `pending_game_auth_config`, (2) headless bypass from `auth_config.json`, (3) mid-run Steam ticket refresh via `_persist_refreshed_ticket`, (4) manual login via `/api/login`. Each path has its own obfuscation/deobfuscation step and writes to both runtime and userdata locations. A failure in any write path leaves credentials in an inconsistent state across the two copies.
- Safe modification: Always test all four auth paths. The `_save_auth_config_both()` helper (line 389) writes to both locations with independent try/except blocks, so a partial failure is logged but not raised.
- Test coverage: No auth-path integration tests exist.

**Event Choice Resolution:**
- Files: `career_bot/events.py` (776 lines), `career_bot/event_outcomes.py` (571 lines)
- Why fragile: Event choice resolution merges data from 4 sources in priority order: (1) preset-level `event_overrides`, (2) legacy global `event_overrides.json`, (3) the event outcomes knowledge base (`event_outcomes.json`, 274KB), and (4) the scraped effects database (`event_effects_scraped.json`, 1.2MB). The merge logic is spread across `EventManager._load()`, `_read_runtime_overrides()`, and the `choose_option()` method. A data format change in any source silently falls through to the next priority level rather than raising an error.
- Safe modification: Add assertions on the expected data shape after loading each source. The test `test_sweepymodv544_event_outcomes.py` covers the basic import flow but not the 4-way merge resolution.
- Test coverage: Partial -- import/export tested, multi-source merge not tested.

**Career Loop Manager:**
- Files: `main.py` (lines 5384-5475, `manage_career_loop`)
- Why fragile: The loop manages consecutive career runs in a background thread, sharing mutable globals (`active_client`, `active_account`, `backend_loop_stop`) with the FastAPI event loop. The loop uses `time.sleep(1)` polling in 5 different places. Consecutive failure counting (`consecutive_fails`) and the guest-parent daily borrow cap interact in subtle ways -- a TP recovery failure counts toward the failure cap even though it is not a career failure.
- Safe modification: Test loop edge cases by mocking `start_career_from_request` to return various failure modes. Verify that `backend_loop_stop` is checked at every blocking point.
- Test coverage: `test_sweepymodv525_umabot_stability.py` exists but tests a limited set of loop scenarios.

## Scaling Limits

**Single-threaded career execution:**
- Current capacity: One career at a time per Python process. The `manage_career_loop` function runs careers sequentially.
- Limit: Multi-account support requires spawning multiple `main.py` processes via `manager.py`, each consuming ~200-400MB RAM (Python + data files + Frida).
- Scaling path: The manager process model is already in place. Memory usage per instance could be reduced by sharing loaded data files across processes (memory-mapped files or a shared data service).

**In-memory career history:**
- Current capacity: `COMPLETED_CAREER_HISTORY` (line 727) is a Python list that grows without bound during a session. Each entry contains the full `chara_info` dict, factor arrays, and race results.
- Limit: After hundreds of careers in a single session, memory usage grows linearly.
- Scaling path: Cap the list (currently uncapped) or persist to disk with an LRU window.

## Dependencies at Risk

**frida (v17.9.1):**
- Risk: Frida is a binary dependency that requires native compilation and must match the target process architecture. It is imported unconditionally at module level (`main.py` line 48) even when running in headless-bypass mode where Frida is never used. Frida version updates frequently break backward compatibility with older game versions.
- Impact: Installation failures on some Windows environments. Blocks startup if Frida fails to import even when the headless bypass would have succeeded.
- Migration plan: Make Frida an optional import -- only import it inside `refresh_auth_before_serving()` when headless bypass fails. Wrap the import in a try/except so headless-only users don't need Frida installed.

**curl_cffi (v0.7.4):**
- Risk: `curl_cffi` is used as the HTTP client in `uma_api/client.py` instead of `requests` for TLS fingerprint impersonation. It has native C dependencies and can be difficult to install on some systems. It is less widely maintained than `requests` or `httpx`.
- Impact: If `curl_cffi` breaks or is abandoned, the entire API client layer must be rewritten.
- Migration plan: Abstract the HTTP session behind an interface so `requests` or `httpx` can be swapped in. The TLS fingerprint requirement may be removable if the game server doesn't check it.

**scipy (>=1.11):**
- Risk: Used for MILP optimization in the smart race solver (`career_bot/trackblazer.py`). Large dependency (~30MB) for a feature that could potentially use a simpler solver.
- Impact: Increases install size and time. Some users have reported scipy installation issues on older Python versions.
- Migration plan: Evaluate if PuLP or a custom greedy solver could replace the scipy MILP for the race planning problem.

## Missing Critical Features

**No API input validation beyond Pydantic:**
- Problem: While Pydantic models validate request structure, there is no business-logic validation layer. For example, `/api/career/start` accepts arbitrary `card_id` values without checking them against the user's owned characters. Invalid IDs are passed through to the game API which may return cryptic error codes.
- Blocks: Clear error messages for invalid configurations. Users must debug game API error codes (102, 500, 2511) themselves.

**No structured logging:**
- Problem: All logging uses `print()` with `flush=True`. There are 100+ print statements scattered across `main.py` and the career bot modules. No log levels, no log rotation, no structured format.
- Blocks: Production debugging, log aggregation, filtering by severity. Log files in `uma_runtime/manager_logs/` grow unbounded.

## Test Coverage Gaps

**`main.py` is entirely untested:**
- What's not tested: All 141 API endpoints, the career loop manager, auth credential lifecycle, timing/pacing engine, userdata resolution, settings persistence, the Frida JS injection code, and startup initialization.
- Files: `main.py` (7787 lines, 0 test lines covering it)
- Risk: Any refactoring of the main file has no safety net. The FastAPI app cannot be imported in tests because it performs side effects at import time (reads settings files, initializes Frida, resolves userdata, starts background threads).
- Priority: High -- this file contains the majority of the application logic.

**`uma_api/client.py` has no direct tests:**
- What's not tested: The `UmaClient` class, API request packing/unpacking, retry logic (network retries, HTTP 5xx retries, result_code 205/208/394 retries), Steam ticket generation, hardware ID spoofing.
- Files: `uma_api/client.py` (1126 lines)
- Risk: Retry logic changes (e.g., adjusting `retry_208` or `retry_394` counts) could cause infinite loops or premature failures. The `pack`/`unpack` crypto functions have no round-trip tests.
- Priority: High -- this is the entire game API communication layer.

**No integration tests for the full career run flow:**
- What's not tested: The complete career lifecycle from start -> turns -> events -> races -> skills -> finish is never tested end-to-end. Individual components (scorer, profiles, trackblazer, events) are tested in isolation.
- Files: `tests/` (104 test files, mostly unit/component level)
- Risk: Interaction bugs between the runner, strategy, events, items, and API client are only caught in production.
- Priority: Medium -- unit tests cover individual decision logic well, but integration is the gap.

**Timing/delay system has zero tests:**
- What's not tested: `wait_for_game_turn_delay()` distribution properties, `attach_turn_delay()` wrapping, `dna_sleep()` behavior, speed level transitions.
- Files: `main.py` (lines 1069-1260), `career_bot/delay.py` (197 lines)
- Risk: Changes to anti-detection pacing could produce detectable timing patterns. No way to verify the distribution is still human-like after modifications.
- Priority: Medium -- the timing system is fragile and security-sensitive.

---

*Concerns audit: 2026-06-27*
