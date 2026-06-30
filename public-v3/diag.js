/* Diag / AI — fetches /api/ai/dashboard + /api/diagnostics/summary. */
(() => {
  'use strict';
  const I = window.Icarus;
  const { api, fmtCompact, esc } = I;
  const $ = (id) => document.getElementById(id);

  let ai = {}, diag = {}, winprob = {};

  // ---- map the real (nested) backend responses to the flat shape this view
  //      renders. The AI dashboard returns success:false when the model hasn't
  //      been trained yet — handle that explicitly instead of rendering blanks. ----
  function relTime(ts) {
    ts = Number(ts) || 0;
    if (!ts) return '—';
    const s = Math.max(0, (Date.now() / 1000) - ts);
    if (s < 90) return Math.round(s) + 's ago';
    if (s < 5400) return Math.round(s / 60) + 'm ago';
    if (s < 129600) return Math.round(s / 3600) + 'h ago';
    return Math.round(s / 86400) + 'd ago';
  }
  function clockOf(ts) {
    ts = Number(ts) || 0;
    if (!ts) return '';
    const d = new Date(ts * 1000);
    return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  }
  const baseName = (p) => String(p || '').split(/[\\/]/).pop();

  function adaptAi(d, status, advisor) {
    const trained = d.success !== false;
    const td = (status && status.turn_decisions) || {};
    const sm = d.shadow_mode || {};
    const auto = d.auto_training || (status && status.auto_training) || {};
    const llm = d.local_llm || auto.local_llm || (status && status.local_llm) || {};
    const cfg = llm.config || {};
    const advice = advisor && (advisor.summary || advisor.advice || advisor.text || advisor.headline || advisor.message);
    const pct = (v) => (v != null ? Math.round(Number(v) * 100) : 0);
    return {
      trained,
      detail: d.detail || '',
      dataset: Number(td.rows ?? td.live_rows ?? 0) || 0,
      accuracy: pct(sm.precision ?? sm.accuracy),
      last_train: relTime(d.updated_at || auto.last_run_at || auto.updated_at),
      shadow_win: pct(sm.precision),
      advisor: advice || (trained ? 'No advisor note for the latest run.' : (d.detail || 'AI not trained yet.')),
      auto_training: !!(auto.enabled ?? auto.running ?? auto.active),
      model_version: d.version || '',
      local_llm: { connected: !!(llm.connected || llm.enabled || llm.ok), endpoint: llm.endpoint || cfg.endpoint || '', model: llm.model || cfg.model || '' },
    };
  }

  function adaptDiag(d) {
    const snap = d.snapshot || {};
    const runner = d.runner || {};
    const md = snap.master_data || snap.masterdata || {};
    const con = [];
    if (d.latest_report) con.push([clockOf(d.latest_report_mtime), 'latest report · ' + baseName(d.latest_report), 'mut']);
    (d.manager_logs || []).slice(0, 4).forEach((p) => con.push(['', 'manager log · ' + baseName(p), 'mut']));
    return {
      server: '● online' + (d.python ? ' · py ' + d.python : ''),
      steam: (runner.logged_in || snap.logged_in || runner.account) ? '● authed' : (d.accounts_exists ? 'configured' : 'not set'),
      userdata: d.runtime_root ? ('set · ' + baseName(d.runtime_root)) : (d.settings_exists ? 'set' : 'not set'),
      master_data: md.status || md.label || (md.stale ? 'stale' : (snap.master_data_version || snap.masterdata_version || '—')),
      console: con,
    };
  }

  function winProbCard() {
    const w = winprob || {};
    const n = Number(w.n_races || 0);
    const min = Number(w.min_races || 25);
    const defk = w.default_k != null ? w.default_k : 150;
    const k = w.fitted_k != null ? w.fitted_k : defk;
    const beats = !!w.beats_baseline;
    const fp = Number(w.field_pairs || 0);
    const fmt = (v) => (v == null ? '—' : v);
    const status = w.healthy ? ['CALIBRATED', 'c-green']
      : n > 0 ? ['LEARNING ' + n + '/' + min, 'c-amber']
        : fp > 0 ? ['FIELD DATA ONLY', 'c-amber']
          : ['AWAITING RACES', 'c-mut'];
    // historical backfill: live progress, else last result, else a hint.
    const bf = w.backfill || {}, lb = w.last_backfill || {};
    let bfTxt;
    if (bf.running) bfTxt = `scanning logs… ${bf.careers_used || 0} careers · ${bf.observations || 0} obs`;
    else if (bf.error) bfTxt = 'backfill error — see server log';
    else if (lb.careers_used != null) bfTxt = `last: ${lb.careers_used} careers · ${lb.observations} obs from ${lb.files_total} logs`;
    else bfTxt = 'feed every past career log into the model';
    return `
      <div class="card" style="padding:13px 14px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><span class="card-title">WIN PROBABILITY MODEL</span><span class="col-meta ${status[1]}">${status[0]}</span></div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
          <div class="statbox"><div class="statbox-k">RACES</div><div class="statbox-v">${n}</div><div class="statbox-sub c-mut">${min} to calibrate</div></div>
          <div class="statbox"><div class="statbox-k">LOGISTIC k</div><div class="statbox-v" style="color:var(--cyan)">${fmt(k)}</div><div class="statbox-sub c-mut">default ${defk}</div></div>
          <div class="statbox"><div class="statbox-k">BRIER</div><div class="statbox-v">${fmt(w.brier)}</div><div class="statbox-sub ${beats ? 'c-green' : 'c-mut'}">${beats ? 'beats' : 'vs'} base ${fmt(w.baseline_brier)}</div></div>
          <div class="statbox"><div class="statbox-k">FIELD AUC</div><div class="statbox-v" style="color:var(--amber)">${fmt(w.field_concordance)}</div><div class="statbox-sub c-mut">${fp} pairs</div></div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;margin-top:11px">
          <button class="abtn cyan" type="button" data-act="winprob-backfill"${bf.running ? ' disabled' : ''}>${bf.running ? 'BACKFILLING…' : 'BACKFILL FROM LOGS'}</button>
          <span class="col-meta c-mut" style="font:500 var(--fs-sm) var(--mono)">${esc(bfTxt)}</span>
        </div>
      </div>`;
  }

  function aiView() {
    const untrained = !ai.trained ? `
      <div class="card" style="border-color:var(--amber-dk)">
        <div class="card-body"><p class="rcard-text" style="margin:0;color:var(--amber)">${esc(ai.detail || 'AI model not trained yet — run Train Now or let auto-training build it. Dataset counts + system health below are live.')}</p></div>
      </div>` : '';
    return `
      ${untrained}
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">
        <div class="statbox"><div class="statbox-k">DATASET</div><div class="statbox-v">${fmtCompact(ai.dataset)}</div><div class="statbox-sub c-mut">turn decisions</div></div>
        <div class="statbox"><div class="statbox-k">ACCURACY</div><div class="statbox-v cyan" style="color:var(--cyan)">${ai.accuracy}%</div><div class="statbox-sub c-mut">model precision</div></div>
        <div class="statbox"><div class="statbox-k">LAST TRAIN</div><div class="statbox-v">${esc(ai.last_train)}</div><div class="statbox-sub">auto-training</div></div>
        <div class="statbox"><div class="statbox-k">SHADOW WIN</div><div class="statbox-v" style="color:var(--amber)">${ai.shadow_win}%</div><div class="statbox-sub">vs live policy</div></div>
      </div>
      ${winProbCard()}
      <div class="card">
        <div class="card-head"><span class="card-title">TRAINING PIPELINE</span><span class="col-meta c-green">auto-training ${ai.auto_training ? 'ON' : 'OFF'}</span></div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:13px 14px">
          <button class="abtn cyan" type="button" data-act="rebuild">REBUILD DATASET</button>
          <button class="abtn cyan" type="button" data-act="import">IMPORT LOGS</button>
          <button class="abtn amber" type="button" data-act="train">TRAIN NOW</button>
          <button class="abtn" type="button" data-act="download">DOWNLOAD MODEL</button>
        </div>
      </div>
      <div style="display:flex;gap:14px">
        <div class="card" style="flex:1">
          <div class="card-head"><span class="card-title">ADVISOR · LATEST</span></div>
          <div class="card-body">
            <p class="rcard-text" style="margin-bottom:10px">${esc(ai.advisor)}</p>
            <div style="display:flex;gap:6px"><button class="abtn cyan" type="button" data-act="postrun">VIEW POST-RUN</button><button class="abtn cyan" type="button" data-act="backtest">BACKTEST</button></div>
          </div>
        </div>
        <div class="card" style="flex:1">
          <div class="card-head"><span class="card-title">LOCAL LLM</span><span class="col-meta ${ai.local_llm && ai.local_llm.connected ? 'c-green' : 'c-mut'}">${ai.local_llm && ai.local_llm.connected ? 'connected' : 'off'}</span></div>
          <div class="card-body" style="display:flex;flex-direction:column;gap:8px">
            <label style="display:flex;flex-direction:column;gap:4px;font:600 var(--fs-2xs) var(--cond);letter-spacing:.14em;color:var(--label)">ENDPOINT
              <input id="ai-llm-endpoint" class="numf" type="text" placeholder="http://127.0.0.1:11434" value="${esc((ai.local_llm || {}).endpoint || '')}"></label>
            <label style="display:flex;flex-direction:column;gap:4px;font:600 var(--fs-2xs) var(--cond);letter-spacing:.14em;color:var(--label)">MODEL
              <input id="ai-llm-model" class="numf" type="text" placeholder="llama3.1" value="${esc((ai.local_llm || {}).model || '')}"></label>
            <div style="display:flex;gap:6px;margin-top:4px"><button class="abtn" type="button" data-act="llm-save">SAVE</button><button class="abtn cyan" type="button" data-act="llm-test">TEST</button><button class="abtn cyan" type="button" data-act="llm-analyze">ANALYZE RUN</button></div>
          </div>
        </div>
      </div>`;
  }

  function diagView() {
    return `
      <div class="card">
        <div class="card-head"><span class="card-title">SYSTEM HEALTH</span></div>
        <div class="card-body" style="display:flex;flex-direction:column;gap:9px">
          ${diagRow('FastAPI server', diag.server, 'green')}
          ${diagRow('Steam bridge', diag.steam, 'green')}
          ${diagRow('Userdata path', diag.userdata, 'ink-2')}
          ${diagRow('Master data', diag.master_data, 'amber')}
        </div>
      </div>
      <div class="card">
        <div class="card-head"><span class="card-title">BUNDLES &amp; EXPORTS</span></div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;padding:13px 14px">
          <button class="abtn cyan" type="button">EXPORT LOGS</button>
          <button class="abtn cyan" type="button">DEBUG BUNDLE</button>
          <button class="abtn cyan" type="button">CRASH TRACE</button>
          <button class="abtn cyan" type="button">DIAG SUMMARY</button>
        </div>
      </div>
      <div class="card">
        <div class="card-head"><span class="card-title">USERDATA</span></div>
        <div class="card-body"><p class="rcard-text is-mut" style="margin:0">Userdata folder configured. Settings, presets, accounts, and Steam auth persist across version upgrades. Wire to <span class="c-cyan" style="font-family:var(--mono);font-size:var(--fs-md)">/api/userdata/info</span>.</p></div>
      </div>`;
  }
  function diagRow(k, v, tone) {
    return `<div style="display:flex;justify-content:space-between;font:500 var(--fs-md) var(--mono)"><span class="c-mut">${esc(k)}</span><span class="c-${tone}">${esc(v || '—')}</span></div>`;
  }

  function systemPanel() {
    const console_ = (diag.console || []).map((r) => `
      <div class="mrow" style="grid-template-columns:60px 1fr"><span class="t">${esc(r[0])}</span><span class="ev is-${r[2]}">${esc(r[1])}</span></div>`).join('');
    return `
      <div class="col-head"><span class="col-title">SYSTEM</span><span class="col-meta">127.0.0.1:1616</span></div>
      <div style="padding:13px 16px;border-bottom:1px solid var(--line-soft);display:flex;flex-direction:column;gap:9px">
        ${diagRow('FastAPI server', '● ' + (diag.server || 'online'), 'green')}
        ${diagRow('Steam bridge', '● ' + (diag.steam || 'authed'), 'green')}
        ${diagRow('Userdata path', diag.userdata || 'set', 'ink-2')}
        ${diagRow('Master data', diag.master_data || 'stale · 3d', 'amber')}
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:11px 16px;border-bottom:1px solid var(--line-soft)">
        <button class="abtn cyan" type="button" data-modal="userdata">USERDATA FOLDER</button>
        <button class="abtn cyan" type="button" data-modal="discord">DISCORD WEBHOOK</button>
      </div>
      <div style="display:flex;align-items:center;gap:8px;padding:10px 16px;border-bottom:1px solid var(--line-soft)">
        <span class="card-title">CONSOLE</span><span class="fbtn is-active">ALL</span><span class="fbtn">WARN</span><span class="fbtn">ERROR</span>
      </div>
      <div class="monitor-rows">${console_}</div>
      <div style="display:flex;align-items:center;gap:8px;padding:10px 16px;border-top:1px solid var(--line-soft)">
        <span class="card-title">LIVE API</span><span class="col-meta" id="diag-stream-meta">/api/stream · SSE</span>
      </div>
      <div class="monitor-rows" id="diag-stream-rows" style="max-height:220px;overflow-y:auto;overflow-x:hidden"></div>`;
  }

  // Live game-API call feed via Server-Sent Events (/api/stream). Additive, isolated
  // to this page; the dashboard keeps polling. EventSource auto-reconnects.
  let _es = null;
  function startStream() {
    if (_es || typeof EventSource === 'undefined') return;
    try { _es = new EventSource('/api/stream'); } catch (e) { return; }
    _es.onmessage = (e) => {
      let d;
      try { d = JSON.parse(e.data); } catch (_) { return; }
      const rows = $('diag-stream-rows');
      if (!rows || !d || d.dir === 'OPEN') return;
      const tone = d.dir === 'ERR' ? 'red' : (d.rc && d.rc !== 1 ? 'amber' : 'mut');
      const row = document.createElement('div');
      row.className = 'mrow';
      row.style.gridTemplateColumns = '54px 1fr 46px';
      row.innerHTML = `<span class="t">${esc(clockOf(d.ts))}</span>`
        + `<span class="ev is-${tone}">${esc(d.dir + ' ' + (d.ep || ''))}</span>`
        + `<span class="t" style="text-align:right">${esc(d.rc != null ? 'rc' + d.rc : (d.err ? 'err' : ''))}</span>`;
      rows.insertBefore(row, rows.firstChild);
      while (rows.children.length > 50) rows.removeChild(rows.lastChild);
    };
    _es.onerror = () => {};  // transient; EventSource reconnects on its own
  }


  // ---- AI action wiring: buttons -> the existing /api/ai/* endpoints ----
  let curSub = 'ai';
  async function loadData() {
    const [aiData, statusData, advisorData, diagData, wpData] = await Promise.all([
      api('/api/ai/dashboard'), api('/api/ai/status'),
      api('/api/ai/advisor/latest'), api('/api/diagnostics/summary'),
      api('/api/race/win-prob-calibration'),
    ]);
    ai = adaptAi(aiData || {}, statusData || {}, advisorData || {});
    diag = adaptDiag(diagData || {});
    winprob = wpData || {};
  }
  async function aiCall(method, url, body) {
    try {
      const opts = { method };
      if (body !== undefined) { opts.headers = { 'Content-Type': 'application/json' }; opts.body = JSON.stringify(body); }
      const r = await fetch(url, opts);
      return await r.json();
    } catch (e) { return { success: false, detail: String(e) }; }
  }
  function showResult(title, data) {
    I.modal({ title: title, sub: 'AI', body: `<pre style="white-space:pre-wrap;word-break:break-word;font:500 var(--fs-sm)/1.6 var(--mono);color:var(--ink-2);margin:0;max-height:60vh;overflow:auto">${esc(JSON.stringify(data, null, 2))}</pre>` });
  }
  async function refreshAi() { await loadData(); render(curSub); }
  // One-off historical backfill: kick the background job, then poll the
  // calibration endpoint until the runner thread reports it's done.
  let _bfPolling = false;
  async function runWinProbBackfill() {
    await aiCall('POST', '/api/race/win-prob-backfill');
    if (_bfPolling) return;
    _bfPolling = true;
    let polls = 0;
    const tick = async () => {
      polls += 1;
      await loadData();
      render(curSub);
      const bf = (winprob && winprob.backfill) || {};
      if (bf.running && polls < 80) { setTimeout(tick, 2500); return; }
      _bfPolling = false;
    };
    await loadData(); render(curSub);          // immediate "BACKFILLING…" state
    setTimeout(tick, 2500);
  }

  async function handleAiAction(act, btn) {
    if (act === 'winprob-backfill') { await runWinProbBackfill(); return; }
    const label = btn.textContent;
    btn.textContent = '…'; btn.disabled = true;
    try {
      let res;
      if (act === 'rebuild') res = await aiCall('POST', '/api/ai/rebuild-dataset');
      else if (act === 'train') res = await aiCall('POST', '/api/ai/train-now');
      else if (act === 'postrun') res = await aiCall('GET', '/api/ai/post-run/latest');
      else if (act === 'backtest') res = await aiCall('GET', '/api/ai/backtest/latest');
      else if (act === 'llm-test') res = await aiCall('POST', '/api/ai/local-llm/test');
      else if (act === 'llm-analyze') res = await aiCall('POST', '/api/ai/local-llm/analyze-latest-run', {});
      else if (act === 'llm-save') res = await aiCall('POST', '/api/ai/local-llm/config', { endpoint: (($('ai-llm-endpoint') || {}).value || '').trim(), model: (($('ai-llm-model') || {}).value || '').trim() });
      else if (act === 'download') { window.location.href = '/api/ai/model/download'; res = { success: true, detail: 'Model download started (404 if no model has been trained yet).' }; }
      else if (act === 'import') {
        const p = (window.prompt('Paste the path to an old build/runtime folder or a logs .zip:') || '').trim();
        if (!p) return;
        res = await aiCall('POST', '/api/ai/import-logs', { source_path: p, rebuild_dataset: true });
      }
      if (res) showResult(label, res);
      if (['rebuild', 'train', 'import', 'llm-save', 'llm-analyze'].indexOf(act) >= 0) refreshAi();
    } finally { btn.textContent = label; btn.disabled = false; }
  }

  function render(sub) {
    curSub = sub;
    // `typeof` guards keep this working in public builds where the raw-API panel
    // (and its RAW API sub-tab) are stripped out.
    let left;
    if (sub === 'diag') left = diagView();
    else if (sub === 'rawapi' && typeof rawApiView === 'function') left = rawApiView();
    else left = aiView();
    $('diag-left').innerHTML = left;
    $('diag-right').innerHTML = systemPanel();
    $('diag-model').innerHTML = '● model ' + (ai.model_version ? 'healthy' : 'untrained');
    $('diag-version').textContent = (ai.model_version || 'v—') + ' · ' + fmtCompact(ai.dataset) + ' samples';
    if (sub === 'rawapi' && typeof wireRawApi === 'function') wireRawApi();
  }

  async function boot() {
    I.mountChrome();
    document.addEventListener('click', (e) => {
      const t = e.target.closest('[data-modal]');
      if (t && I.Modals && I.Modals[t.dataset.modal]) { I.Modals[t.dataset.modal](); return; }
      const b = e.target.closest('[data-act]');
      if (b) handleAiAction(b.dataset.act, b);
    });
    await loadData();
    render('ai');
    startStream();
    document.querySelectorAll('.seg[data-sub]').forEach((s) => s.addEventListener('click', () => {
      document.querySelectorAll('.seg[data-sub]').forEach((x) => x.classList.remove('is-active'));
      s.classList.add('is-active');
      render(s.dataset.sub);
    }));
  }
  boot();
})();
