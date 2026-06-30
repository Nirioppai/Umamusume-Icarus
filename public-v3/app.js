/* ============================================================
   ICARUS · Command Console (v3) — dashboard logic
   Vanilla, no build step. Talks to the SAME API as the old UI
   (GET /api/career/runner every 1.5s). When the backend is not
   reachable, api() returns null, the OFFLINE banner shows, and the
   last render is kept (empty/idle on first load). No simulated data.
   Start `python main.py` and the real data takes over.
   ============================================================ */
(() => {
  'use strict';

  // ---------- tiny helpers ----------
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtNum = (n) => (Number(n) || 0).toLocaleString('en-US');
  const fmtCompact = (n) => {
    n = Number(n) || 0;
    if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    return String(n);
  };
  const pad2 = (n) => String(n).padStart(2, '0');
  const hpTone = (hp) => hp < 35 ? 'red' : hp <= 60 ? 'amber' : 'green';

  // ---------- cool-dash: shared utils ----------
  // Lazy-inject our own stylesheet once (mirrors core.js ensureFontLink). Keeps
  // all the add-on styling out of styles.css per the file-ownership rule.
  function ensureCoolDashCss() {
    const id = 'cd-coolstyle';
    if (document.getElementById(id)) return;
    const l = document.createElement('link');
    l.id = id; l.rel = 'stylesheet'; l.href = 'cool-dash.css?v=2';
    (document.head || document.documentElement).appendChild(l);
  }
  const _rmm = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  const reducedMotion = () => !!(_rmm && _rmm.matches);
  const lsGet = (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };

  // ---------- runtime state ----------
  const state = {
    runner: null,
    account: null,
    reasonTab: 'decision',
    logHist: {},      // turn -> action row  (accumulated archive)
    reasonHist: {},   // turn -> decision card (accumulated archive)
    lastAttrPct: {},  // attr key -> last-rendered bar %  (so bars animate on change)
    devToggles: { tempt: false, burn: false, loop: false, finish: false },
  };

  // ============================================================
  //  API LAYER — real fetch; returns null when the backend is unreachable.
  // ============================================================
  async function api(url, opts = {}) {
    try {
      const ctrl = new AbortController();
      // 12s (not 4s): a real career's /api/career/runner snapshot (up to 300
      // action_history rows, ~50-250KB) can take several seconds to fetch+parse
      // on the first poll or modest hardware. A 4s abort wrongly tripped mock.
      const timer = setTimeout(() => ctrl.abort(), 12000);
      const res = await fetch(url, { ...opts, signal: ctrl.signal });
      clearTimeout(timer);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const json = await res.json();
      const mb = $('mockbar'); if (mb) mb.classList.remove('show');
      return json;
    } catch (e) {
      // Backend unreachable / transient failure → show the offline notice and
      // return null. No simulated data is ever produced; callers keep the last
      // render (or render an empty/idle state on first load).
      const mb = $('mockbar'); if (mb) mb.classList.add('show');
      return null;
    }
  }

  // ============================================================
  //  RENDER
  // ============================================================
  // Free race-retry continue readout for the navbar. Shows the live free-continue
  // count and, when the free pool is empty, an ESTIMATED next-refresh countdown
  // (free continues refresh daily; free_continue_time is the daily stamp, rolled
  // forward to the next future occurrence). Data comes from the live career's
  // home_info via the runner status (runner.clocks); hidden until a career sets it.
  function freeClockPill() {
    const rc = (state.runner && state.runner.clocks) || null;
    if (!rc || !rc.seen) return '';
    let suffix = '';
    if (rc.free <= 0 && rc.refreshAt > 0) {
      let target = rc.refreshAt;
      const now = Date.now() / 1000;
      while (target <= now) target += 86400;   // daily refresh; roll to the next one
      const secs = target - now;
      const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60);
      suffix = `<span class="sub"> ~${h}h${String(m).padStart(2, '0')}</span>`;
    }
    const tone = rc.free > 0 ? ' is-amber' : ' is-dim';
    const title = `Free race-retry continues (refresh daily). Free now: ${rc.free}, standard clocks: ${rc.std}.`
      + (suffix ? ' The ~time is the estimated next daily free refresh.' : '');
    return `<div class="pill" title="${title}"><div class="pill-k">FREE CLK</div><div class="pill-v${tone}">${rc.free}${suffix}</div></div>`;
  }

  function renderPills(account) {
    const host = $('rail-pills');
    if (!host) return;
    // Don't rebuild the rail while the user is interacting with the native
    // TP-recovery <select>: the dashboard runs THIS renderPills (not core.js's
    // guarded copy) on the 1.5s poll, and the innerHTML rebuild was collapsing
    // the open dropdown mid-hover. Skip the rebuild while it's focused/open.
    const ae = document.activeElement;
    if (ae && ae.classList && ae.classList.contains('recov-sel') && host.contains(ae)) return;
    const tp = account.tp || {};
    const c = account.carrots || {};
    const html = `
      <div class="pill"><div class="pill-k">TP</div><div class="pill-v">${pad2(tp.current || 0)}<span class="sub">/${tp.max || 0}</span></div></div>
      ${window.Icarus && Icarus.recoveryPill ? Icarus.recoveryPill() : ''}
      <div class="pill"><div class="pill-k">CARROTS</div><div class="pill-v is-amber">${fmtNum(c.total)}</div></div>
      <div class="pill"><div class="pill-k">GOLD</div><div class="pill-v">${fmtCompact(account.gold)}</div></div>
      <div class="pill"><div class="pill-k">CLOCKS</div><div class="pill-v">${fmtNum(account.clocks)}</div></div>
      ${freeClockPill()}
      ${window.Icarus && Icarus.careerPillHtml ? Icarus.careerPillHtml(account.career) : ''}`;
    host.innerHTML = html;
  }

  function renderVitals(runner) {
    const t = runner.trainee || {};
    $('trainee-name').textContent = t.name || 'NO CAREER';
    $('trainee-meta').textContent = `${t.scenario || '—'} · ${t.rank || ''} · T${runner.turn || 0}`.replace(' ·  ·', ' ·');
    $('portrait-live').innerHTML = runner.running ? '◷ live' : '◷ idle';
    $('portrait-live').className = 'portrait-live ' + (runner.running ? 'c-cyan' : 'c-mut');

    const hp = runner.hp ?? 0;
    const tone = hpTone(hp);
    const hpLabel = $('hp-label');
    hpLabel.textContent = tone === 'red' ? 'HP · CRITICAL' : tone === 'amber' ? 'HP · LOW' : 'HP';
    hpLabel.className = 'hp-label ' + (tone === 'red' ? 'c-red' : tone === 'amber' ? 'c-amber' : 'c-mut');
    $('hp-num').innerHTML = `${pad2(runner.hpRaw ?? hp)}<span class="sub">/${runner.hpMax ?? 100}</span>`;
    const fill = $('hp-fill');
    fill.style.width = hp + '%';
    fill.className = 'hp-fill fill-' + tone;
    if (tone === 'red') fill.style.animation = 'critpulse 1.1s infinite'; else fill.style.animation = '';

    const mood = runner.mood || {};
    const mv = $('mood-v');
    mv.textContent = mood.label ? `${mood.label} · ${mood.value}` : '—';
    mv.className = 'kv-v c-' + (mood.tone || 'mut');
    $('fans-v').textContent = fmtCompact(runner.fans || 0);

    const list = $('attr-list');
    list.innerHTML = '';
    const animBars = [];
    (runner.stats || []).forEach((s) => {
      const pct = Math.min(100, Math.round((s.v / (s.max || 600)) * 100));
      // SP always glows amber; the last-trained stat glows green; nothing else glows.
      const glow = s.accent ? 'amber' : (s.trained ? 'green' : null);
      // Start the bar at its previous width so the CSS transition animates the rise
      // (innerHTML rebuilds the element each poll, so a fresh bar wouldn't animate).
      const prev = state.lastAttrPct[s.k];
      const startPct = (prev == null) ? pct : prev;
      const row = el('div', 'attr');
      row.innerHTML = `
        <span class="attr-k${glow ? ' c-' + glow : ''}">${s.k}</span>
        <div class="attr-track"><div class="attr-bar${glow ? ' fill-' + glow : ''}" style="width:${startPct}%"></div></div>
        <span class="attr-v${glow ? ' c-' + glow : ''}">${s.v}</span>`;
      list.appendChild(row);
      animBars.push([row.querySelector('.attr-bar'), pct]);
      state.lastAttrPct[s.k] = pct;
    });
    requestAnimationFrame(() => animBars.forEach(([b, p]) => { if (b) b.style.width = p + '%'; }));

    // Lifetime metrics now live in the navbar (Icarus.renderLifetime), not here.
    cdAfterVitals(runner);   // cool-dash: radar swap + ECG/mood instruments (#1, #2)
  }

  function renderLog(runner) {
    // accumulate every turn we see — never drop earlier turns
    (runner.action_rows || []).forEach((r) => { if (r && r.turn != null) state.logHist[r.turn] = r; });
    const rows = Object.values(state.logHist).sort((a, b) => a.turn - b.turn);
    $('feed-meta').textContent = `${rows.length} TURN${rows.length === 1 ? '' : 'S'} · ${runner.running ? 'LIVE' : 'IDLE'}`;
    const wrap = $('log-rows');
    if (!rows.length) { wrap.innerHTML = '<div class="feed-idle">Awaiting career signal — press <b>RUN CAREER</b> to begin.</div>'; return; }
    const stick = wrap.scrollTop + wrap.clientHeight >= wrap.scrollHeight - 4;      // following live → keep pinned to newest (bottom)
    const prev = wrap.scrollTop;
    wrap.innerHTML = '';
    rows.forEach((r, i) => {
      // HP tone is by PERCENTAGE of the turn's max-HP, so it stays accurate as the
      // ceiling grows over a career (raw thresholds would read "green" forever).
      const frac = r.hpmax ? (r.hp / r.hpmax) : (r.hp / 100);
      const hpClr = frac <= 0.18 ? 'red' : frac <= 0.42 ? 'amber' : 'green';
      const moodClr = (typeof r.mood === 'number') ? (r.mood >= 4 ? 'green' : r.mood === 3 ? 'amber' : 'red') : 'mut';
      const row = el('div', 'log-row' + (i === 0 ? ' is-current' : ''));
      row.innerHTML = `
        <span class="log-turn">${r.turn}</span>
        <span class="log-act"><span class="rcard-badge bg-${r.actTone}">${r.act}</span></span>
        <span class="log-target${r.act === 'REST' || r.act === 'REC' ? ' is-mut' : ''}">${esc(r.target)}${r.win ? ' <span class="log-1st">1ST</span>' : ''}</span>
        <span class="log-hp r c-${hpClr}">${pad2(r.hp)}</span>
        <span class="log-mood r c-${moodClr}">${r.mood ?? '—'}</span>`;
      wrap.appendChild(row);
    });
    wrap.scrollTop = stick ? wrap.scrollHeight : prev;
    cdScanWins(runner);      // cool-dash: tiny win pop at the 1ST badge on a freshly-seen win (#4)
  }

  // ---- Shop-item icons (game8 source), keyed by the in-game item name as it
  //      appears in decision-reasoning text. Served from /api/item-icons/<id>.<ext>.
  //      Ported from the old UI so the Decision Reasoning panel shows item icons. ----
  const ITEM_ICON_MAP = {
    'Speed Notepad': '/api/item-icons/1001.jpg', 'Stamina Notepad': '/api/item-icons/1002.png',
    'Power Notepad': '/api/item-icons/1003.png', 'Guts Notepad': '/api/item-icons/1004.png',
    'Wit Notepad': '/api/item-icons/1005.png',
    'Speed Manual': '/api/item-icons/1101.png', 'Stamina Manual': '/api/item-icons/1102.png',
    'Power Manual': '/api/item-icons/1103.png', 'Guts Manual': '/api/item-icons/1104.png',
    'Wit Manual': '/api/item-icons/1105.jpg',
    'Speed Scroll': '/api/item-icons/1201.png', 'Stamina Scroll': '/api/item-icons/1202.png',
    'Power Scroll': '/api/item-icons/1203.jpg', 'Guts Scroll': '/api/item-icons/1204.png',
    'Wit Scroll': '/api/item-icons/1205.png',
    'Vita 20': '/api/item-icons/2001.png', 'Vita 40': '/api/item-icons/2002.png',
    'Vita 65': '/api/item-icons/2003.png', 'Royal Kale Juice': '/api/item-icons/2101.png',
    'Energy Drink MAX': '/api/item-icons/2201.png', 'Energy Drink MAX EX': '/api/item-icons/2202.png',
    'Plain Cupcake': '/api/item-icons/2301.jpg', 'Berry Sweet Cupcake': '/api/item-icons/2302.png',
    'Yummy Cat Food': '/api/item-icons/3001.png', 'Grilled Carrots': '/api/item-icons/3101.jpg',
    'Pretty Mirror': '/api/item-icons/4001.jpg', "Reporter's Binoculars": '/api/item-icons/4002.png',
    'Master Practice Guide': '/api/item-icons/4003.png', "Scholar's Hat": '/api/item-icons/4004.png',
    'Fluffy Pillow': '/api/item-icons/4101.png', 'Pocket Planner': '/api/item-icons/4102.png',
    'Rich Hand Cream': '/api/item-icons/4103.png', 'Smart Scale': '/api/item-icons/4104.png',
    'Aroma Diffuser': '/api/item-icons/4105.png', 'Practice Drills DVD': '/api/item-icons/4106.png',
    'Miracle Cure': '/api/item-icons/4201.png',
    'Speed Training Application': '/api/item-icons/5001.png', 'Stamina Training Application': '/api/item-icons/5002.png',
    'Power Training Application': '/api/item-icons/5003.png', 'Guts Training Application': '/api/item-icons/5004.png',
    'Wit Training Application': '/api/item-icons/5005.png',
    'Reset Whistle': '/api/item-icons/7001.png',
    'Coaching Megaphone': '/api/item-icons/8001.png', 'Motivating Megaphone': '/api/item-icons/8002.png',
    'Empowering Megaphone': '/api/item-icons/8003.png',
    'Speed Ankle Weights': '/api/item-icons/9001.png', 'Stamina Ankle Weights': '/api/item-icons/9002.png',
    'Power Ankle Weights': '/api/item-icons/9003.png', 'Guts Ankle Weights': '/api/item-icons/9004.png',
    'Good-Luck Charm': '/api/item-icons/10001.png',
    'Artisan Cleat Hammer': '/api/item-icons/11001.png', 'Master Cleat Hammer': '/api/item-icons/11002.png',
    'Glow Sticks': '/api/item-icons/11003.png',
  };
  let _itemIconRegex = null;
  const _itemIconByEscaped = {};
  function _ensureItemIconRegex() {
    if (_itemIconRegex) return;
    const names = Object.keys(ITEM_ICON_MAP).sort((a, b) => b.length - a.length); // longest-first
    const alts = names.map((n) => {
      const e = esc(n);
      _itemIconByEscaped[e] = { name: n, path: ITEM_ICON_MAP[n] };
      return e.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    });
    _itemIconRegex = new RegExp('(' + alts.join('|') + ')', 'g');
  }
  // Prepend each shop item's icon before its name in already-esc'd reason text.
  function decorateItemIcons(escapedText) {
    if (!escapedText) return escapedText;
    _ensureItemIconRegex();
    return escapedText.replace(_itemIconRegex, (m) => {
      const hit = _itemIconByEscaped[m];
      if (!hit) return m;
      return `<img class="reason-item-icon" src="${hit.path}" alt="" title="${m}" loading="lazy" onerror="this.style.display='none'">${m}`;
    });
  }
  function itemChip(name) {
    const path = ITEM_ICON_MAP[name];
    const icon = path ? `<img class="reason-item-icon" src="${path}" alt="" loading="lazy" onerror="this.style.display='none'">` : '';
    return `<span class="chip">${icon}${esc(name)}</span>`;
  }

  function renderReasoning(runner) {
    // accumulate every decision card we see (do this even on the profile tab)
    (runner.reasoning || []).forEach((r) => { if (r && r.turn != null) state.reasonHist[r.turn] = r; });
    const body = $('reason-body');
    const cards = Object.values(state.reasonHist).sort((a, b) => a.turn - b.turn);
    if (!cards.length) { body.innerHTML = '<div class="feed-idle">Decision reasoning will stream here once a career is running.</div>'; return; }
    const stick = body.scrollTop + body.clientHeight >= body.scrollHeight - 4;
    const prev = body.scrollTop;
    body.innerHTML = '';
    cards.forEach((r, i) => {
      const fromEnd = (cards.length - 1) - i;   // 0 = most recent turn
      const cls = fromEnd === 0 ? 'is-current' : fromEnd <= 2 ? 'is-faded' : 'is-dim';
      const card = el('div', 'rcard ' + cls);
      const items = (r.items && r.items.length)
        ? `<div class="rcard-items"><span class="k">ITEMS</span>${r.items.map((it) => itemChip(it)).join('')}</div>` : '';
      const turnCls = fromEnd === 0 ? 'is-amber' : 'is-mut';
      const mutCls = fromEnd !== 0 ? ' is-mut' : '';
      // Per-turn reasoning as bullet points (a clean single <p> when there's just one line).
      const lines = (r.lines && r.lines.length) ? r.lines : (r.text ? [r.text] : []);
      const bodyHtml = lines.length > 1
        ? `<ul class="rcard-lines${mutCls}">${lines.slice(0, 6).map((l) => `<li>${decorateItemIcons(esc(l))}</li>`).join('')}</ul>`
        : `<p class="rcard-text${mutCls}">${decorateItemIcons(esc(lines[0] || ''))}</p>`;
      card.innerHTML = `
        <div class="rcard-head">
          <span class="rcard-turn ${turnCls}">${esc(r.title)}</span>
          <span class="rcard-badge bg-${r.badgeBg}">${esc(r.badge)}</span>
        </div>
        ${r.sub ? `<div class="rcard-sub">${esc(r.sub)}</div>` : ''}
        ${bodyHtml}
        ${items}`;
      body.appendChild(card);   // outer #reason-body DOM node (was shadowed by the html string)
    });
    body.scrollTop = stick ? body.scrollHeight : prev;
  }

  function renderMonitor(runner) {
    $('monitor-meta').textContent = `turn ${runner.turn || 0} · ${runner.running ? 'live' : 'idle'}`;
    const wrap = $('monitor-rows');
    wrap.innerHTML = '';
    (runner.monitor || []).forEach((m) => {
      const row = el('div', 'mrow');
      row.innerHTML = `<span class="t">${m.time}</span><span class="tn">T${m.turn}</span><span class="ev is-${m.evTone}">${esc(m.ev)}</span><span class="dt">${esc(m.detail)}</span>`;
      wrap.appendChild(row);
    });
    const legend = $('stat-legend');
    if (!legend.childElementCount && runner.stats) {
      const colors = { SPD: '#36c5d0', STA: '#4ade80', PWR: '#f04444', GUT: '#c084fc', SP: '#f2a900' };
      legend.innerHTML = runner.stats.filter((s) => colors[s.k]).map((s) =>
        `<span><span class="swatch" style="background:${colors[s.k]}"></span>${s.k} ${s.v}</span>`).join('');
    }
  }

  function renderLive(runner) {
    const live = $('tab-live');
    const txt = $('tab-live-text');
    live.className = 'tab-live ' + (runner.running ? '' : runner.paused ? 'is-paused' : 'is-idle');
    txt.textContent = runner.status_text || (runner.running ? 'RUNNING' : 'IDLE');

    const running = runner.running, paused = runner.paused;
    $('run-btn').disabled = running;
    $('run-btn').textContent = runner.finished ? 'RUN AGAIN' : 'RUN CAREER';
    $('stop-btn').disabled = !running && !paused;
    $('pause-btn').disabled = !running && !paused;
    $('pause-btn').textContent = paused ? 'RESUME' : 'PAUSE';
  }

  function render(snap) {
    if (!snap || !snap.runner) return;
    state.runner = snap.runner;
    state.account = snap.account;
    if (snap.account) renderPills(snap.account);
    renderVitals(snap.runner);
    renderLog(snap.runner);
    renderReasoning(snap.runner);
    renderLive(snap.runner);
  }

  // ============================================================
  //  COOL-DASH  — dashboard UI upgrades (lazy-injected stylesheet).
  //  Tasteful, offline, vanilla treatments hooked off the existing render
  //  functions + state.runner: attribute RADAR (with TARGET-GHOST), vitals
  //  ECG/mood instruments, a tiny WIN POP at the 1ST badge, a typed RUN-CAREER
  //  boot sequence, and EVENT TOASTS (skill buys / career errors). All
  //  animation degrades to static under prefers-reduced-motion. Namespaced `cd*`.
  // ============================================================
  const cd = {
    radarOn: lsGet('cd_attr_radar', '0') === '1',
    instrOn: lsGet('cd_vitals_instr', '0') === '1',
    seenWins: new Set(),          // race turns we've already celebrated (#4 win pop)
    bootTimer: null, bootAbort: null,
    toastHost: null,
    targetCache: null,            // active preset's per-stat target (radar ghost)
    targetFetchAt: 0,             // last fetch time (ms) — refreshed lazily
    seenSkills: new Set(),        // skill names already toasted (event-toast de-dupe)
    seenSkillCount: -1,           // last-seen skills_bought count
    lastErrorSig: null,           // last career-error string already toasted
  };

  // ---- 1) ATTRIBUTE RADAR -----------------------------------------------
  // Build the toggle button beside the ATTRIBUTES title (once), then render
  // either the flat bars (renderVitals does that) or our SVG pentagon.
  const RADAR_KEYS = ['SPD', 'STA', 'PWR', 'GUT', 'WIT'];   // 5 axes (excludes SP)
  const RADAR_CAP = 1200;
  const RADAR_CAP_REF = 1100;     // fallback "cap ref" target when no real target exists

  // Resolve the per-stat TARGET for the radar's faint ghost pentagon, in priority:
  //   (a) preset mant_config.global_stat_target  (gated by enable_global_stat_target)
  //   (b) preset mant_config.stat_targets_by_distance  → per-stat MAX across distances
  //   (c) a flat cap-reference at RADAR_CAP_REF / RADAR_CAP
  // Returns { vals:[SPD,STA,PWR,GUT,WIT], real:bool, label:string } or null while
  // the (lazy, cached) fetch is still pending. The target order matches RADAR_KEYS.
  function cdResolveTarget() {
    if (cd.targetCache) return cd.targetCache;
    // cap-reference is always available immediately as a safe default
    return { vals: RADAR_KEYS.map(() => RADAR_CAP_REF), real: false, label: 'cap ref' };
  }
  function cdComputeTargetFromPreset(payload) {
    const presets = (payload && payload.presets) || [];
    const active = (payload && payload.active) || '';
    let p = presets.find((x) => x && String(x.name) === String(active)) || presets[0] || null;
    const mc = (p && p.mant_config) || {};
    // (a) global stat target (only when explicitly enabled)
    const g = mc.global_stat_target;
    if (mc.enable_global_stat_target && Array.isArray(g) && g.length >= 5) {
      return { vals: g.slice(0, 5).map((n) => Number(n) || 0), real: true, label: 'target' };
    }
    // (b) per-distance targets → take the per-stat MAX across all defined distances
    //     (the practical ceiling you'd want for your best distance; avoids needing
    //     the trainee's live distance aptitude wired into the snapshot).
    const byDist = mc.stat_targets_by_distance;
    if (byDist && typeof byDist === 'object') {
      const rows = Object.values(byDist).filter((r) => Array.isArray(r) && r.length >= 5);
      if (rows.length) {
        const vals = [0, 0, 0, 0, 0];
        rows.forEach((r) => { for (let i = 0; i < 5; i++) vals[i] = Math.max(vals[i], Number(r[i]) || 0); });
        return { vals, real: true, label: 'target' };
      }
    }
    // (c) cap reference
    return { vals: RADAR_KEYS.map(() => RADAR_CAP_REF), real: false, label: 'cap ref' };
  }
  // Lazily fetch the active preset's targets (cached ~60s). Re-renders the radar
  // once on first resolution so the ghost appears without waiting for a stat change.
  function cdEnsureTargets() {
    const now = Date.now();
    if (cd.targetCache && (now - cd.targetFetchAt) < 60000) return;
    if (cd._targetFetching) return;
    cd._targetFetching = true;
    fetch('/api/settings-presets?t=' + now)
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        cd._targetFetching = false;
        if (!j) return;
        cd.targetCache = cdComputeTargetFromPreset(j);
        cd.targetFetchAt = Date.now();
        if (cd.radarOn && state.runner) cdRenderRadar(state.runner.stats || []);   // show the ghost now
      })
      .catch(() => { cd._targetFetching = false; });
  }
  function cdEnsureRadarToggle() {
    const title = document.querySelector('.vitals .attr-title');
    if (!title || title.dataset.cdRow) return;
    title.dataset.cdRow = '1';
    const row = el('div', 'attr-title-row');
    title.parentNode.insertBefore(row, title);
    row.appendChild(title);
    const btn = el('button', 'cd-radar-toggle' + (cd.radarOn ? ' on' : ''), cd.radarOn ? 'BARS' : 'RADAR');
    btn.type = 'button';
    btn.title = 'Toggle attribute radar / bars';
    btn.addEventListener('click', () => {
      cd.radarOn = !cd.radarOn;
      lsSet('cd_attr_radar', cd.radarOn ? '1' : '0');
      btn.classList.toggle('on', cd.radarOn);
      btn.textContent = cd.radarOn ? 'BARS' : 'RADAR';
      state.lastAttrPct = {};                       // force bars to re-seed when we switch back
      if (state.runner) renderVitals(state.runner);  // immediate swap
    });
    row.appendChild(btn);
  }
  // SVG pentagon radar. Vertices tween via CSS (transition on cx/cy/points).
  function cdRenderRadar(stats) {
    const list = $('attr-list');
    if (!list) return;
    const byK = {}; (stats || []).forEach((s) => { byK[s.k] = s; });
    const n = RADAR_KEYS.length, R = 78, cx = 110, cy = 100;
    const ang = (i) => (-Math.PI / 2) + (i * 2 * Math.PI / n);   // start at top
    const ptAt = (i, r) => [cx + r * Math.cos(ang(i)), cy + r * Math.sin(ang(i))];
    // current data points (clamped to the 1200 cap)
    const valpoly = [], vals = [];
    RADAR_KEYS.forEach((k, i) => {
      const s = byK[k] || { v: 0 };
      const frac = Math.max(0.02, Math.min(1, (s.v || 0) / RADAR_CAP));
      valpoly.push(ptAt(i, R * frac).map((v) => v.toFixed(1)));
      vals.push(s.v || 0);
    });
    const polyStr = valpoly.map((p) => p.join(',')).join(' ');
    // TARGET-GHOST: a second, faint pentagon drawn BEHIND the current polygon
    // showing the per-stat target (or a cap reference). Same axes/cap mapping.
    cdEnsureTargets();
    const tgt = cdResolveTarget();
    const tgtStr = RADAR_KEYS.map((_, i) => {
      const frac = Math.max(0.02, Math.min(1, (Number(tgt.vals[i]) || 0) / RADAR_CAP));
      return ptAt(i, R * frac).map((v) => v.toFixed(1)).join(',');
    }).join(' ');
    let svg = list.querySelector('svg.cd-radar');
    // Build the static scaffold (rings + spokes + axis keys) ONCE; afterward only
    // the polygon points / vertex positions / value labels are updated in place so
    // the CSS transitions on points/cx/cy tween the shape when stats change.
    if (!svg) {
      const ringPts = (r) => RADAR_KEYS.map((_, i) => ptAt(i, r).map((v) => v.toFixed(1)).join(',')).join(' ');
      let rings = '';
      [0.25, 0.5, 0.75, 1].forEach((f) => { rings += `<polygon class="cd-ring" points="${ringPts(R * f)}"/>`; });
      let spokes = '', labels = '', dots = '';
      RADAR_KEYS.forEach((k, i) => {
        const edge = ptAt(i, R);
        spokes += `<line class="cd-spoke" x1="${cx}" y1="${cy}" x2="${edge[0].toFixed(1)}" y2="${edge[1].toFixed(1)}"/>`;
        dots += `<circle class="cd-vtx" data-i="${i}" cx="${valpoly[i][0]}" cy="${valpoly[i][1]}" r="2.6"/>`;
        const lp = ptAt(i, R + 16);
        const anchor = Math.abs(lp[0] - cx) < 6 ? 'middle' : (lp[0] > cx ? 'start' : 'end');
        const dy = lp[1] < cy - 4 ? 0 : (lp[1] > cy + 4 ? 9 : 4);
        labels += `<text class="cd-axis-k" x="${lp[0].toFixed(1)}" y="${(lp[1] + dy).toFixed(1)}" text-anchor="${anchor}">${k}</text>`
                + `<text class="cd-axis-v" data-i="${i}" x="${lp[0].toFixed(1)}" y="${(lp[1] + dy + 11).toFixed(1)}" text-anchor="${anchor}">${vals[i]}</text>`;
      });
      // The ghost polygon is emitted BEFORE the current polygon so it paints behind.
      list.innerHTML = `<div class="cd-radar-wrap">
        <svg class="cd-radar" viewBox="0 0 220 200" role="img" aria-label="Attribute radar">
          ${rings}${spokes}
          <polygon class="cd-ghost" points="${tgtStr}"/>
          <polygon class="cd-poly" points="${polyStr}"/>
          ${dots}${labels}
        </svg></div>
        <div class="cd-radar-legend">
          <span class="cd-lg cd-lg-cur"><i></i>current</span>
          <span class="cd-lg cd-lg-tgt ${tgt.real ? 'is-real' : 'is-ref'}"><i></i>${esc(tgt.label)}</span>
        </div>`;
      return;
    }
    // in-place update → CSS tweens the vertices/polygon
    const poly = svg.querySelector('.cd-poly');
    if (poly) poly.setAttribute('points', polyStr);
    const ghost = svg.querySelector('.cd-ghost');
    if (ghost) ghost.setAttribute('points', tgtStr);
    svg.querySelectorAll('.cd-vtx').forEach((c) => {
      const i = Number(c.dataset.i);
      c.setAttribute('cx', valpoly[i][0]); c.setAttribute('cy', valpoly[i][1]);
    });
    svg.querySelectorAll('.cd-axis-v').forEach((t) => {
      const i = Number(t.dataset.i);
      if (String(vals[i]) !== t.textContent) t.textContent = vals[i];
    });
    // keep the target-legend label in sync (real target vs cap reference)
    const lgTgt = list.querySelector('.cd-radar-legend .cd-lg-tgt');
    if (lgTgt) {
      lgTgt.classList.toggle('is-real', !!tgt.real);
      lgTgt.classList.toggle('is-ref', !tgt.real);
      const txtNode = lgTgt.childNodes[lgTgt.childNodes.length - 1];
      if (txtNode && txtNode.nodeType === 3 && txtNode.textContent !== tgt.label) txtNode.textContent = tgt.label;
    }
  }

  // ---- 2) VITALS GAUGES + ECG HEARTLINE ---------------------------------
  function cdEnsureInstrToggle() {
    const head = document.querySelector('.vitals .hp-head');
    if (!head || head.dataset.cdInstr) return;
    head.dataset.cdInstr = '1';
    const lbl = head.querySelector('.hp-label');
    const btn = el('button', 'cd-instr-toggle' + (cd.instrOn ? ' on' : ''), 'ECG');
    btn.type = 'button';
    btn.title = 'Toggle ECG heartline + mood gauge';
    btn.addEventListener('click', () => {
      cd.instrOn = !cd.instrOn;
      lsSet('cd_vitals_instr', cd.instrOn ? '1' : '0');
      btn.classList.toggle('on', cd.instrOn);
      cdSyncInstruments();
    });
    // Insert as a SIBLING of .hp-label (not a child) — renderVitals rewrites the
    // label's textContent every poll, which would otherwise destroy the button.
    if (lbl && lbl.parentNode === head) lbl.insertAdjacentElement('afterend', btn);
    else head.appendChild(btn);
    // mount points (after the HP track, before the kv rows)
    const track = head.parentNode.querySelector('.hp-track');
    if (track && !head.parentNode.querySelector('.cd-ecg')) {
      const ecg = el('div', 'cd-ecg'); ecg.id = 'cd-ecg';
      track.parentNode.insertBefore(ecg, track.nextSibling);
      const gauge = el('div', 'cd-gauge'); gauge.id = 'cd-gauge'; gauge.style.display = 'none';
      ecg.parentNode.insertBefore(gauge, ecg.nextSibling);
    }
  }
  // A repeating ECG waveform path; the visible window scrolls (CSS sweep). The
  // colour tracks HP tone, and the beat period shortens as HP drops to critical.
  function cdEcgPath(w, h) {
    // one "beat" cell ~ 70px wide; baseline + a QRS spike
    const mid = h * 0.5, cell = 70, pts = [];
    for (let x = 0; x <= w; x += 2) {
      const p = (x % cell) / cell; let y = mid;
      if (p > 0.40 && p < 0.46) y = mid - h * 0.06;        // P
      else if (p >= 0.46 && p < 0.50) y = mid + h * 0.10;  // Q
      else if (p >= 0.50 && p < 0.54) y = mid - h * 0.42;  // R spike
      else if (p >= 0.54 && p < 0.58) y = mid + h * 0.22;  // S
      else if (p > 0.66 && p < 0.74) y = mid - h * 0.12;   // T
      pts.push(x + ',' + y.toFixed(1));
    }
    return pts.join(' ');
  }
  function cdRenderEcg(runner) {
    const host = $('cd-ecg');
    if (!host) return;
    const hp = runner.hp ?? 0;
    const tone = hpTone(hp);
    const crit = tone === 'red';
    // beat quickens at low HP (reuse the critpulse idea): 1.6s healthy → .55s critical
    const beat = (0.55 + (Math.max(0, Math.min(100, hp)) / 100) * 1.05).toFixed(2) + 's';
    host.style.setProperty('--cd-ecg-beat', beat);
    host.classList.toggle('crit', crit && !reducedMotion());
    const W = 280, H = 38;
    const sweepCls = reducedMotion() ? '' : ' cd-ecg-sweep';
    const path = cdEcgPath(W, H);
    // draw two copies side-by-side so the translateX sweep is seamless
    host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
      <g class="${sweepCls.trim()}" style="transform-box:view-box">
        <polyline class="cd-ecg-line t-${tone}" points="${path}"/>
        <polyline class="cd-ecg-line t-${tone}" points="${path}" transform="translate(${W} 0)"/>
      </g></svg>`;
  }
  // Compact arc gauge for MOOD (motivation 1-5).
  function cdRenderMoodGauge(runner) {
    const g = $('cd-gauge');
    if (!g) return;
    const mood = runner.mood || {};
    const val = Number(mood.value) || 0;
    const frac = Math.max(0, Math.min(1, val / 5));
    const tone = mood.tone && mood.tone !== 'mut' ? mood.tone : 'cyan';
    const stroke = `var(--${tone})`;
    const r = 18, c = 2 * Math.PI * r, off = (c * (1 - frac)).toFixed(1);
    g.innerHTML = `
      <svg viewBox="0 0 46 46" aria-label="Mood gauge">
        <circle class="cd-gauge-track" cx="23" cy="23" r="${r}"/>
        <circle class="cd-gauge-arc" cx="23" cy="23" r="${r}"
          stroke="${stroke}" stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${off}"
          transform="rotate(-90 23 23)"/>
      </svg>
      <div class="cd-gauge-meta">
        <div class="cd-gauge-k">MOOD</div>
        <div class="cd-gauge-v c-${tone}">${esc(mood.label || '—')}${val ? ' · ' + val : ''}</div>
      </div>`;
  }
  function cdSyncInstruments() {
    const ecg = $('cd-ecg'), g = $('cd-gauge');
    if (ecg) ecg.classList.toggle('on', cd.instrOn);
    if (g) g.style.display = cd.instrOn ? 'flex' : 'none';
    if (cd.instrOn && state.runner) { cdRenderEcg(state.runner); cdRenderMoodGauge(state.runner); }
  }

  // Called at the tail of every renderVitals (see hook below).
  function cdAfterVitals(runner) {
    cdEnsureRadarToggle();
    cdEnsureInstrToggle();
    if (cd.radarOn) cdRenderRadar(runner.stats || []);   // replaces the bars renderVitals just drew
    cdSyncInstruments();
  }

  // ---- 4) WIN POP (tiny localized burst at the 1ST badge) ---------------
  function cdConfettiColors() {
    const cs = getComputedStyle(document.documentElement);
    const amber = (cs.getPropertyValue('--amber') || '#f2a900').trim();
    const green = (cs.getPropertyValue('--green') || '#4ade80').trim();
    const cyan = (cs.getPropertyValue('--cyan') || '#36c5d0').trim();
    return [amber, amber, amber, green, cyan, '#ffffff'];
  }
  // A small, localized particle pop centred on (px, py) viewport coords — the
  // on-screen position of the winning row's 1ST badge. ~14 tiny particles,
  // short radius/duration. Tiny fixed canvas around the origin (not full-screen).
  function cdFireWinPop(px, py) {
    if (reducedMotion()) return;
    const BOX = 120;                                   // canvas half-extent ~ pop radius
    const cv = el('canvas', 'cd-winpop');
    cv.style.left = (px - BOX) + 'px';
    cv.style.top = (py - BOX) + 'px';
    cv.style.width = (BOX * 2) + 'px';
    cv.style.height = (BOX * 2) + 'px';
    document.body.appendChild(cv);
    const ctx = cv.getContext('2d');
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = BOX * 2 * dpr; cv.height = BOX * 2 * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const cx = BOX, cy = BOX;                           // origin in canvas space
    const colors = cdConfettiColors();
    const N = 12 + ((Math.random() * 7) | 0), parts = []; // 12-18 particles
    for (let i = 0; i < N; i++) {
      const ang = (i / N) * Math.PI * 2 + (Math.random() - 0.5) * 0.5;
      const spd = 2.2 + Math.random() * 3.4;           // small radius
      parts.push({
        x: cx, y: cy, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd - 1.2,
        g: 0.14 + Math.random() * 0.08, w: 3 + Math.random() * 3, h: 2 + Math.random() * 3,
        rot: Math.random() * Math.PI, vr: (Math.random() - 0.5) * 0.4,
        c: colors[(Math.random() * colors.length) | 0],
      });
    }
    const t0 = performance.now(), DUR = 700;            // short duration
    function frame(now) {
      const t = now - t0;
      ctx.clearRect(0, 0, BOX * 2, BOX * 2);
      let alive = false;
      parts.forEach((p) => {
        p.vy += p.g; p.vx *= 0.97; p.x += p.vx; p.y += p.vy; p.rot += p.vr;
        const a = Math.max(0, 1 - t / DUR);
        if (a > 0) alive = true;
        ctx.save();
        ctx.globalAlpha = a; ctx.translate(p.x, p.y); ctx.rotate(p.rot);
        ctx.fillStyle = p.c; ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      });
      if (alive && t < DUR) requestAnimationFrame(frame);
      else cv.remove();
    }
    requestAnimationFrame(frame);
  }
  // Find the 1ST badge of the NEWEST winning row (data-turn === the won turn) and
  // emit the pop at its centre. Falls back to no pop if the badge isn't on screen.
  function cdPopAtBadge(turn) {
    const wrap = $('log-rows');
    if (!wrap) return;
    let badge = null;
    wrap.querySelectorAll('.log-row').forEach((row) => {
      const t = row.querySelector('.log-turn');
      if (t && Number(t.textContent) === Number(turn)) {
        const b = row.querySelector('.log-1st');
        if (b) badge = b;
      }
    });
    if (!badge) return;
    const r = badge.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;        // not laid out / off screen
    cdFireWinPop(r.left + r.width / 2, r.top + r.height / 2);
  }
  // Detect NEW wins from the just-rendered log. Only celebrate during a running
  // career and never replay old wins across poll re-renders (seenWins is seeded
  // silently on the first snapshot we ever see).
  function cdScanWins(runner) {
    const rows = (runner && runner.action_rows) || [];
    const wins = rows.filter((r) => r && r.win === true).map((r) => Number(r.turn));
    if (cd.seenWins.size === 0 && !cd._winSeeded) {
      // first observation of this run: record without celebrating
      wins.forEach((t) => cd.seenWins.add(t));
      cd._winSeeded = true;
      return;
    }
    const fresh = wins.filter((t) => !cd.seenWins.has(t));
    fresh.forEach((t) => cd.seenWins.add(t));
    if (fresh.length && runner.running) {
      const newest = fresh[fresh.length - 1];
      // renderLog has already (re)built the rows for this poll — pop at the badge
      // after layout settles so getBoundingClientRect reads the final position.
      requestAnimationFrame(() => cdPopAtBadge(newest));
      cdEventToast('1ST PLACE', 'G1/Race win on T' + newest, 'amber');
    }
  }

  // ---- EVENT TOASTS (new skill buys / career errors) --------------------
  // Prefer the shared navbar toaster (window.Icarus.toast); fall back to the
  // local cdToast. Single entry point so every cool-dash toast routes the same.
  function cdEventToast(title, msg, tone) {
    if (window.Icarus && Icarus.toast) { try { Icarus.toast(title + ' — ' + msg, tone); return; } catch (e) {} }
    cdToast(title, msg, tone);
  }
  // Pull the bought-skill names out of the raw action_history rows (the runner
  // appends purchased skill names onto each turn's row under `skills`).
  function cdSkillNamesFromRaw(raw) {
    const runner = (raw && raw.runner) || {};
    const ah = Array.isArray(runner.action_history) ? runner.action_history : [];
    const names = [];
    ah.forEach((e) => { ((e && Array.isArray(e.skills)) ? e.skills : []).forEach((nm) => { if (nm) names.push(String(nm)); }); });
    return names;
  }
  // Fire toasts for events detected BETWEEN polls. De-duped so the same skill /
  // error never re-toasts on subsequent polls. Seeds silently on the first
  // observation of a run so an in-progress resume doesn't dump a backlog.
  function cdScanEvents(snap, raw) {
    const runner = (raw && raw.runner) || {};
    const adapted = (snap && snap.runner) || {};
    const running = !!runner.running;

    // (i) NEW skill purchase — count rose (skills_bought) and/or new names appear.
    const count = Number(runner.skills_bought || 0);
    const names = cdSkillNamesFromRaw(raw);
    const firstObs = (cd.seenSkillCount < 0);
    if (firstObs) {
      // seed silently: remember the baseline so we only toast genuinely-new buys
      cd.seenSkillCount = count;
      names.forEach((nm) => cd.seenSkills.add(nm));
    } else {
      const newNames = names.filter((nm) => !cd.seenSkills.has(nm));
      newNames.forEach((nm) => cd.seenSkills.add(nm));
      const countRose = count > cd.seenSkillCount;
      cd.seenSkillCount = Math.max(cd.seenSkillCount, count);
      if (running && (newNames.length || countRose)) {
        if (newNames.length) {
          const shown = newNames.slice(0, 3).join(', ') + (newNames.length > 3 ? ` +${newNames.length - 3} more` : '');
          cdEventToast('SKILL LEARNED', shown, 'cyan');
        } else {
          // count rose but no names surfaced (older/locked rows) — generic notice
          cdEventToast('SKILL LEARNED', '+1 skill purchased', 'cyan');
        }
      }
    }

    // (ii) career ERROR / CRASH — last_error newly set, or a crashed/stuck state.
    const err = String(runner.last_error || '').trim();
    const crashed = !!(runner.crashed || runner.stuck);
    const sig = err || (crashed ? 'CRASHED' : '');
    if (sig && sig !== cd.lastErrorSig) {
      cd.lastErrorSig = sig;
      cdEventToast('CAREER ERROR', err || 'Career crashed / stuck — see Diagnostics.', 'red');
    } else if (!sig) {
      cd.lastErrorSig = null;   // cleared upstream → allow the next error to toast
    }
  }

  // ---- 5) CAREER BOOT SEQUENCE ------------------------------------------
  function cdAbortBoot() {
    if (cd.bootTimer) { clearTimeout(cd.bootTimer); cd.bootTimer = null; }
    if (cd.bootAbort) { try { cd.bootAbort(); } catch (e) {} cd.bootAbort = null; }
    const o = document.getElementById('cd-boot'); if (o) o.remove();
  }
  function cdStartBoot(traineeName) {
    cdAbortBoot();
    const feed = document.querySelector('.feed');
    if (!feed) return;
    const lines = [
      ['<span class="acc">ICARUS</span> // amber console online', 0],
      ['AUTH … <span class="ok">ok</span>', 1],
      ['LOADING TRAINEE … <span class="acc">' + esc(traineeName || 'standby') + '</span>', 1],
      ['ENGINE: <span class="acc">trackblazer</span>', 1],
      ['SSE LINK … <span class="ok">established</span>', 1],
      ['<span class="dim">awaiting first turn…</span>', 0],
    ];
    const overlay = el('div', 'cd-boot'); overlay.id = 'cd-boot';
    overlay.title = 'click to skip';
    feed.appendChild(overlay);
    overlay.addEventListener('click', cdAbortBoot, { once: true });
    if (reducedMotion()) {                   // no typing — show all lines, auto-clear
      overlay.innerHTML = lines.map((l) => `<div class="cd-boot-line">${l[0]}</div>`).join('');
      cd.bootTimer = setTimeout(cdAbortBoot, 1500);
      return;
    }
    let li = 0, ci = 0, tags = '';   // tags = the completed lines (accumulates across li)
    // strip tags for char-by-char typing, then swap to the rich line when complete
    function stripped(html) { const d = document.createElement('div'); d.innerHTML = html; return d.textContent || ''; }
    let cancelled = false;
    cd.bootAbort = () => { cancelled = true; };
    function typeStep() {
      if (cancelled) return;
      if (li >= lines.length) { cd.bootTimer = setTimeout(cdAbortBoot, 350); return; }
      const full = lines[li][0];
      const text = stripped(full);
      if (ci <= text.length) {
        overlay.innerHTML = tags
          + `<div class="cd-boot-line">${esc(text.slice(0, ci))}<span class="cd-boot-caret"></span></div>`;
        ci++;
        cd.bootTimer = setTimeout(typeStep, 16 + Math.random() * 22);
      } else {
        tags += `<div class="cd-boot-line done">${full}</div>`;   // swap to the rich (tagged) line
        overlay.innerHTML = tags;
        li++; ci = 0;
        cd.bootTimer = setTimeout(typeStep, 90 + lines[Math.min(li, lines.length - 1)][1] * 70);
      }
    }
    typeStep();
  }

  // ---- toast (use Icarus.toast if present, else a tiny local fallback) ----
  function cdToast(title, msg, tone) {
    if (window.Icarus && Icarus.toast) { try { Icarus.toast(title + ' — ' + msg, tone); return; } catch (e) {} }
    if (reducedMotion()) return;
    if (!cd.toastHost) { cd.toastHost = el('div', 'cd-toast-host'); document.body.appendChild(cd.toastHost); }
    const toneCls = tone === 'red' ? ' t-red' : tone === 'cyan' ? ' t-cyan' : '';
    const t = el('div', 'cd-toast' + toneCls);
    t.innerHTML = `<span class="cd-toast-t">${esc(title)}</span> · ${esc(msg)}`;
    cd.toastHost.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3400);
  }

  // ---- init: run once at boot ----
  function cdInit() {
    ensureCoolDashCss();
  }

  // ============================================================
  //  REAL-BACKEND ADAPTER
  //  Maps the live /api/career/runner payload ({success, runner,
  //  account}) into the view-model the redesign renders. Live state
  //  is in runner.current_chara; per-turn rows in runner.action_history;
  //  mood is motivation 1-5; lifetime in runner.lifetime.
  // ============================================================
  function fmtDur(s) {
    s = Number(s) || 0;
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    if (h) return h + 'h ' + m + 'm';
    if (m) return m + 'm';
    return (s | 0) + 's';
  }
  const MOOD_MAP = { 5: ['Great', 'green'], 4: ['Good', 'green'], 3: ['Normal', 'cyan'], 2: ['Bad', 'amber'], 1: ['Awful', 'red'] };
  // Live status carries scenario_id (int), not a label; this bot runs Trackblazer (4).
  const SCENARIO_MAP = { 4: 'TRACKBLAZER' };
  function moodFromMotivation(m) {
    const e = MOOD_MAP[Number(m)] || ['—', 'mut'];
    return { label: e[0], value: Number(m) || '', tone: e[1] };
  }
  // Tones match the preview/mock: TRAIN green, RACE amber, REST cyan, REC purple.
  const ACT_META = {
    train: ['TRAIN', 'green'], rest: ['REST', 'cyan'], recreation: ['REC', 'purple'],
    recreate: ['REC', 'purple'], race: ['RACE', 'amber'], race_progress: ['RACE', 'amber'],
    finish: ['FINISH', 'green'], medic: ['MEDIC', 'red'], infirmary: ['MEDIC', 'red'],
    rest_summer: ['REST', 'cyan'],
  };
  function actMeta(a) {
    a = String(a || '').toLowerCase();
    return ACT_META[a] || [(a.toUpperCase().slice(0, 6)) || '—', 'mut'];
  }
  const FAC_MAP = { '101': 'Speed', '102': 'Stamina', '103': 'Power', '104': 'Guts', '105': 'Wit' };
  // Live action rows put a stat summary (HP 80/100 | MOOD 4 | SPD … ) in `detail`,
  // which must never be used as a human label or reasoning sentence.
  const isStatDump = (s) => /^\s*HP\s*\d/i.test(String(s || '')) || /\bSPD\s*\d+\s*STA\s*\d+/i.test(String(s || ''));
  const cleanDetail = (r) => { const d = r && r.detail; return (d && !isStatDump(d)) ? d : ''; };
  function facLabel(r) {
    const a = String(r.action || '').toLowerCase();
    const fac = String(r.facility || '').trim();
    const numeric = /^\d+$/.test(fac);
    // race: facility holds the race label (e.g. "Satsuki Sho \u00b7 G1 \u00b7 2000m \u00b7 Turf").
    if (a === 'race' || a === 'race_progress') return fac || cleanDetail(r) || r.race_name || r.name || 'Race';
    // train: facility is ALREADY the stat name ("Speed"/"Stamina"/...) from the
    // backend's TRAINING_LABELS \u2014 so use it directly ("Speed training"), matching
    // the preview, instead of wrapping it as "Facility Speed Training".
    if (a === 'train') {
      if (fac && !numeric) return fac + ' training';
      return (FAC_MAP[fac] ? FAC_MAP[fac] + ' training' : 'Training');
    }
    if (a === 'rest' || a === 'rest_summer') return 'Rest';
    if (a === 'recreation' || a === 'recreate') return 'Recreation';
    if (a === 'medic' || a === 'infirmary') return 'Infirmary';
    if (a === 'finish') return cleanDetail(r) || 'Career Finished';
    return cleanDetail(r) || (fac && !numeric ? fac : (FAC_MAP[fac] ? FAC_MAP[fac] + ' training' : 'Action'));
  }
  // Small category label under each decision card's title (preview style).
  function subFor(a) {
    a = String(a || '').toLowerCase();
    if (a === 'train') return 'GOAL-AWARE SCORER';
    if (a === 'race' || a === 'race_progress') return 'SMART RACE SOLVER';
    if (a === 'rest' || a === 'rest_summer') return 'ENERGY GUARD';
    if (a === 'recreation' || a === 'recreate') return 'MOOD GUARD';
    if (a === 'medic' || a === 'infirmary') return 'INFIRMARY';
    if (a === 'finish') return 'CAREER';
    return '';
  }
  // Per-action reasoning sentence when the live row carries no `reasoning` lines,
  // so cards read like the design instead of dumping the stat summary.
  function reasonFor(r) {
    const a = String(r.action || '').toLowerCase();
    if (a === 'train') return 'Highest goal-weighted training score this turn — support bonuses and mood factored in.';
    if (a === 'race' || a === 'race_progress') return 'Selected by the Smart Race Solver for value on the planned route.';
    if (a === 'rest' || a === 'rest_summer') return 'Energy below threshold — rested to protect HP before the next cluster.';
    if (a === 'recreation' || a === 'recreate') return 'Recreation chosen to lift mood before the next training cluster.';
    if (a === 'medic' || a === 'infirmary') return 'Treated to clear a negative condition before it compounded.';
    if (a === 'finish') return 'Career complete.';
    return 'Highest-scoring action available this turn.';
  }

  function adaptReal(data) {
    const runner = (data && data.runner) || {};
    const account = (data && data.account) || null;
    const cur = runner.current_chara || {};
    const ah = Array.isArray(runner.action_history) ? runner.action_history : [];
    const last = ah.length ? ah[ah.length - 1] : null;
    const lastStats = (last && last.stats) || {};
    const cs = Object.keys(cur.stats || {}).length ? cur.stats : lastStats;

    const hpNow = Number(cur.vital ?? lastStats.hp ?? 0);
    const hpMax = Number(cur.max_vital ?? lastStats.max_hp ?? 100) || 100;
    const motivation = cur.motivation ?? lastStats.motivation;
    const hasCareer = !!(cur.turn || ah.length || runner.running || runner.finished || runner.paused);

    // The bar/value GLOW follows the most recently trained stat (SP keeps its own
    // amber accent always). Walk action_history backwards for the last `train` turn
    // and map its facility ("Speed"/… or 101-105) to a stat key.
    const TRAIN_STAT = {
      speed: 'speed', stamina: 'stamina', power: 'power', guts: 'guts', wit: 'wit', wisdom: 'wit',
      '101': 'speed', '102': 'stamina', '103': 'power', '104': 'guts', '105': 'wit',
    };
    let lastTrained = null;
    for (let j = ah.length - 1; j >= 0; j--) {
      const e = ah[j] || {};
      if (String(e.action || '').toLowerCase() === 'train') {
        const f = String(e.facility || '').trim().toLowerCase().replace(/\s*training$/, '');
        lastTrained = TRAIN_STAT[f] || null;
        break;
      }
    }
    const sRow = (k, key) => ({ k, key, v: Number(cs[key] || 0), max: 1200, trained: key === lastTrained });
    // SP (skill points) can live on the chara top-level OR in either stats dict.
    const skillPoints = Number(cur.skill_point ?? cs.skill_point ?? lastStats.skill_point ?? 0);
    const stats = [
      sRow('SPD', 'speed'), sRow('STA', 'stamina'), sRow('PWR', 'power'),
      sRow('GUT', 'guts'), sRow('WIT', 'wit'),
      // Skill Points row (preview style): bar + number, amber. SP is a spendable
      // resource so the bar is scaled to a soft 700 cap (the number is the truth).
      { k: 'SP', key: 'sp', v: skillPoints, max: 700, accent: true },
    ];

    const wonTurns = new Set(((runner.race_results) || [])
      .filter((rr) => Number(rr.rank ?? rr.final_rank ?? 99) === 1)
      .map((rr) => Number(rr.turn)));
    const action_rows = ah.map((r) => {
      const meta = actMeta(r.action);
      const st = r.stats || {};
      return {
        turn: r.turn, act: meta[0], actTone: meta[1],
        target: facLabel(r),
        hp: Number(st.hp ?? 0),
        hpmax: Number(st.max_hp ?? 100) || 100,
        mood: st.motivation != null ? moodFromMotivation(st.motivation).value : '—',
        win: meta[0] === 'RACE' && wonTurns.has(Number(r.turn)),
      };
    });

    const reasoning = ah.map((r) => {
      const meta = actMeta(r.action);
      // Real reasoning text (old-UI style): the backend's per-turn reasoning lines,
      // else the decision reason, else a generic sentence — never the stat dump.
      // Kept as an ARRAY of lines so the panel renders them as bullet points;
      // esc + icon decoration happens at render time.
      const reasons = Array.isArray(r.reasoning) ? r.reasoning.filter(Boolean) : [];
      const rawLines = reasons.length ? reasons
        : (r.reason && !isStatDump(r.reason) ? [r.reason] : [reasonFor(r)]);
      // strip the engine-name prefix ("trackblazer: " / "summer/finale: ") from each line
      const lines = rawLines.map((l) => String(l).replace(/^\s*(trackblazer|summer\/finale)\s*:\s*/i, ''));
      return {
        turn: r.turn,
        title: `T${r.turn ?? '?'} · ${facLabel(r).toUpperCase()}`,
        badge: meta[0], badgeBg: meta[1],
        sub: subFor(r.action),
        lines,
        items: Array.isArray(r.items) ? r.items.filter(Boolean) : [],
      };
    });

    const lt = runner.lifetime || {};
    const lifetime = {
      total_fan_gain: lt.total_fans_gained_live ?? lt.total_fans_gained ?? runner.fans_gained ?? 0,
      fans_per_hour: lt.fans_per_hour_live ?? runner.fans_per_hour ?? 0,
      runtime: fmtDur(lt.total_runtime_seconds_live ?? lt.total_runtime_seconds ?? 0),
      careers_done: lt.careers_completed ?? runner.careers_completed ?? 0,
      career_fan_gain: cur.fans ?? 0,
    };

    if (account) account.runs = lt.careers_completed ?? account.runs ?? 0;
    const careerName = (account && account.career && account.career.name) || cur.name || 'CAREER';
    const turn = cur.turn || runner.turn || 0;
    // The backend sends scenario_id (int) and no status_text — synthesize both so
    // the vitals line shows the scenario and the live pill shows the turn
    // ("RUNNING · T50"), matching the mock instead of "—" / bare "RUNNING".
    const scenarioId = Number((account && account.career && account.career.scenario_id) ?? runner.scenario_id ?? cur.scenario_id ?? 0);
    const scenario = SCENARIO_MAP[scenarioId] || '';
    const status_text = runner.running ? `RUNNING · T${turn}`
      : runner.paused ? `PAUSED · T${turn}`
      : runner.finished ? 'FINISHED' : 'IDLE';

    return {
      account,
      runner: {
        running: !!runner.running, finished: !!runner.finished, paused: !!runner.paused,
        turn, status_text,
        cardId: Number(cur.card_id || (account && account.career && account.career.card_id) || 0),
        trainee: hasCareer ? { name: careerName, scenario, rank: '' } : {},
        hp: Math.max(0, Math.min(100, Math.round((hpNow / hpMax) * 100))),
        hpRaw: hpNow, hpMax,
        mood: motivation != null ? moodFromMotivation(motivation) : {},
        fans: cur.fans || runner.fans || 0,
        stats: hasCareer ? stats : [],
        lifetime, action_rows, reasoning,
        run_id: runner.run_id || '',   // new-career detection for loop mode (#5)
        clocks: {
          std: Number(runner.standard_clocks || 0),
          free: Number(runner.free_clocks || 0),
          refreshAt: Number(runner.free_continue_time || 0),
          total: Number(runner.clocks_left || 0),
          seen: ('free_clocks' in runner) || ('clocks_left' in runner),
        },
      },
    };
  }

  // ============================================================
  //  POLL LOOP  (mirrors the old UI's bgSetInterval 1.5s cadence)
  // ============================================================
  // ---------- 3D portrait + PNG toggle ----------
  // Single 3D model: the chibi Seiun Sky (model-test/mini.html). It loads ONCE and
  // spins continuously — never reloaded per trainee/career, so the spin stays smooth.
  // A "3D"/"PNG" toggle (bottom-left of the box) swaps to a flat PNG of the active
  // trainee (served from /api/images/<card_id>.png) and back.
  let lastRunId = null;
  let portraitMode = '3d';   // '3d' | 'png'
  let selectedCardId = 0;    // Setup-selected trainee (PNG fallback when no career)
  function setPortrait() {
    const f = $('portrait-3d');
    if (f && !/model-test\/mini\.html/.test(f.getAttribute('src') || '')) f.src = 'model-test/mini.html?v=3';
  }
  // The PNG shows the ACTIVE career trainee, or (when idle) the Setup-selected one.
  async function loadSelectedTrainee() {
    try {
      const r = await fetch('/api/session?t=' + Date.now());
      const j = await r.json();
      selectedCardId = Number((j && j.selection && j.selection.trainee && j.selection.trainee.id) || 0);
      if (portraitMode === 'png') applyPortraitPng();
    } catch (e) { /* keep 0 */ }
  }
  function applyPortraitPng() {
    const img = $('portrait-png');
    if (!img) return;
    const cid = (state.runner && state.runner.cardId) || selectedCardId;
    if (cid) {
      const src = '/api/card-art/' + cid + '.png?v=2';   // 512px standing illustration (?v=2 busts stale cache)
      if (img.getAttribute('src') !== src) img.src = src;
      img.style.display = 'block';
      img.onerror = () => { img.style.display = 'none'; };
    } else {
      img.removeAttribute('src');
      img.style.display = 'none';   // no trainee → empty box, never a broken-image alt
    }
  }
  function setPortraitMode(mode) {
    portraitMode = (mode === 'png') ? 'png' : '3d';
    const f = $('portrait-3d'), img = $('portrait-png'), b = $('portrait-mode'), tag = $('portrait-tag');
    const png = portraitMode === 'png';
    if (f) f.style.display = png ? 'none' : 'block';
    if (img) { img.style.display = png ? 'block' : 'none'; if (png) applyPortraitPng(); }
    if (b) b.textContent = png ? 'PNG' : 'Seiun';
    if (tag) tag.textContent = png ? 'TRAINEE · PNG' : '3D MODEL · .PMX';
  }
  function syncPortrait() { setPortrait(); }

  async function refresh() {
    const raw = await api('/api/career/runner');
    // Offline / transient poll failure → keep the last render and retry next poll.
    if (raw == null) return;
    const snap = adaptReal(raw);
    // New career started (incl. mid-loop): backend run_id changed → drop the old
    // run's accumulated feed/reasoning so the dashboard switches to the new run. (#5)
    const rid = snap.runner && snap.runner.run_id;
    if (rid && rid !== lastRunId) {
      lastRunId = rid; state.logHist = {}; state.reasonHist = {}; state.lastAttrPct = {};
      // new run → reset cool-dash per-run state (wins + event-toast de-dupe)
      cd.seenWins = new Set(); cd._winSeeded = false;
      cd.seenSkills = new Set(); cd.seenSkillCount = -1; cd.lastErrorSig = null;
    }
    render(snap);
    // cool-dash: the first real action row aborts the typed boot overlay (#5) so
    // it never delays data.
    if ((snap.runner.action_rows || []).length) cdAbortBoot();
    // cool-dash: event toasts (new skill buys / career errors) off the same snapshot.
    cdScanEvents(snap, raw);
    // Feed the shared bottom MONITOR dock from the same live snapshot.
    if (window.Icarus && Icarus.setMonitor) Icarus.setMonitor(raw);
    // Bordered lifetime metrics in the navbar + recolour the accent to the active
    // trainee (the dashboard runs its own poll, not core's pollChrome).
    if (window.Icarus && Icarus.renderLifetime) Icarus.renderLifetime(raw.runner);
    if (window.Icarus && Icarus.applyTraineeTheme) {
      const cid = raw.runner && raw.runner.current_chara && raw.runner.current_chara.card_id;
      Icarus.applyTraineeTheme(cid);
    }
    // Keep the PNG portrait fresh if the user is viewing it.
    if (portraitMode === 'png') applyPortraitPng();
  }
  function startPolling() {
    refresh();
    setInterval(refresh, 1500);
  }

  // ============================================================
  //  START CAREER — builds the real /api/career/run payload from the
  //  server-persisted Setup selection (trainee/deck/friend/parents).
  //  Resumes instead when a career is already active.
  // ============================================================
  function flashRun(msg) {
    const b = $('run-btn');
    if (!b) return;
    const prev = b.textContent;
    b.textContent = msg;
    setTimeout(() => { b.textContent = prev; }, 2600);
  }
  async function rawPost(url, body) {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    return res.json();
  }
  // Parents: mirror the old UI's selectedParentStartPayload — own[0]+guest
  // (parent_selection_mode 'own_guest') when a guest parent is picked in Setup,
  // else own[0]+own[1] ('own_own'). Without this the rental fields were dropped
  // and a chosen guest parent was silently ignored at career start.
  function parentStartPayload(sel) {
    const own = (sel.veterans || []).filter(Boolean);
    const guest = (sel.guestParents || []).filter(Boolean)[0] || null;
    if (guest && own[0]) {
      return {
        parent_id_1: Number(own[0].instance_id || 0), parent_id_2: 0,
        rental_viewer_id: Number(guest.viewer_id || 0),
        rental_trained_chara_id: Number(guest.instance_id || guest.id || 0),
        rental_card_id: Number(guest.card_id || 0),
        parent_selection_mode: 'own_guest',
      };
    }
    return {
      parent_id_1: Number((own[0] || {}).instance_id || 0),
      parent_id_2: Number((own[1] || {}).instance_id || 0),
      rental_viewer_id: 0, rental_trained_chara_id: 0, rental_card_id: 0,
      parent_selection_mode: 'own_own',
    };
  }
  // Retry budget from the RETRIES dev popover (core.js devConfig). Sent on every
  // run (fresh + resume), matching the old UI; previously never sent at all.
  function retryStartPayload() {
    const r = (window.Icarus && Icarus.devConfig && Icarus.devConfig.retries) || {};
    const mpr = (typeof r.maxPerRace === 'number') ? r.maxPerRace : -1;  // -1 = use preset/default
    return {
      carats_enabled: !!r.carats,
      max_clocks_per_career: Math.max(0, Number(r.maxClocks) || 0),
      clocks_g1_debut_only: !!r.g1DebutOnly,
      max_retries_per_race: mpr,
    };
  }
  // Read the active preset's persisted race mode + manual race list so a run uses
  // what was set in Setup (Smart plan or hand-picked Manual). The backend also has
  // a defense-in-depth fallback, but sending it explicitly is the correct path.
  async function racePayload() {
    try {
      const r = await fetch('/api/smart-solver/config?t=' + Date.now());
      const j = await r.json();
      const mode = (j && j.source === 'manual') ? 'manual' : 'smart';
      const ids = ((j && j.config && j.config.extra_race_list) || []).map((x) => Number(x)).filter((n) => Number.isFinite(n));
      return { race_planner_mode: mode, manual_race_ids: mode === 'manual' ? ids : [] };
    } catch (e) { return { race_planner_mode: 'smart', manual_race_ids: [] }; }
  }
  async function startCareer() {
    let sess = null;
    try { const r = await fetch('/api/session?t=' + Date.now()); sess = await r.json(); } catch (e) { /* ignore */ }
    const sel = (sess && sess.selection) || {};
    const account = sess && sess.account;
    const active = !!(account && account.career && account.career.active);
    // BUG #6: LOOP is a run-count now (0 = ∞). Fall back to the legacy bool.
    const runCount = (state.devToggles.loopCount != null)
      ? Number(state.devToggles.loopCount)
      : (state.devToggles.loop ? 0 : 1);
    const rp = await racePayload();   // persisted race mode + manual picks from the active preset
    let body;
    if (active) {
      body = {
        preset_name: '', max_steps: 2500, burn_clocks: state.devToggles.burn,
        finalize_single_runs: state.devToggles.finish, dev_mode: runCount !== 1,
        run_count: runCount, ...rp,
        ...retryStartPayload(),
      };
    } else {
      if (!sel.trainee || !sel.trainee.id) { flashRun('PICK A TRAINEE IN SETUP'); return; }
      if (!sel.deck || !(sel.deck.cards || []).length) { flashRun('BUILD/PICK A DECK'); return; }
      if (!sel.friend || !sel.friend.support_card_id) { flashRun('PICK A FRIEND SUPPORT'); return; }
      body = {
        card_id: Number(sel.trainee.id),
        support_card_ids: (sel.deck.cards || []).map((c) => Number(c.id)),
        friend_viewer_id: Number(sel.friend.viewer_id || 0),
        friend_card_id: Number(sel.friend.support_card_id || 0),
        ...parentStartPayload(sel),
        deck_id: Number(sel.deck.id) || 1,
        scenario_id: 4, use_tp: 30, difficulty_id: 0, difficulty: 0, is_boost: 0,
        preset_name: '', max_steps: 2500, burn_clocks: state.devToggles.burn,
        finalize_single_runs: state.devToggles.finish, dev_mode: runCount !== 1,
        run_count: runCount, ...rp,
        ...retryStartPayload(),
      };
    }
    flashRun(active ? 'RESUMING…' : 'STARTING…');
    try {
      const data = await rawPost('/api/career/run', body);
      if (!data || !data.success) flashRun((data && data.detail) ? String(data.detail).slice(0, 32) : 'START FAILED');
    } catch (e) { flashRun('START REQUEST FAILED'); }
    refresh();
  }

  // ============================================================
  //  INTERACTIONS
  // ============================================================
  function bind() {
    // run / stop / pause — POST to the real runner endpoints.
    $('run-btn').addEventListener('click', async () => {
      // cool-dash: typed boot overlay (#5) — only when no live feed is already on
      // screen; the first real row (or a click) aborts it instantly.
      if (!Object.keys(state.logHist).length) {
        const nm = (state.runner && state.runner.trainee && state.runner.trainee.name)
          || ($('trainee-name') && $('trainee-name').textContent !== 'NO CAREER' ? $('trainee-name').textContent : '');
        cdStartBoot(nm);
      }
      await startCareer();
    });
    $('stop-btn').addEventListener('click', async () => {
      await api('/api/career/runner/stop', { method: 'POST' });
      refresh();
    });
    $('pause-btn').addEventListener('click', async () => {
      const paused = state.runner && state.runner.paused;
      await api('/api/career/runner/' + (paused ? 'resume' : 'pause'), { method: 'POST' });
      refresh();
    });

    // reasoning tabs
    $('rt-decision').addEventListener('click', () => setReasonTab('decision'));

    // 3D / PNG portrait toggle (bottom-left of the model box)
    { const pm = $('portrait-mode'); if (pm) pm.addEventListener('click', () => setPortraitMode(portraitMode === '3d' ? 'png' : '3d')); }

    // dev toggles (tempt + retries are popovers, wired by Icarus.bindDevExtras)
    // Share core.js's single devToggles object so the state is one source of
    // truth across every page; core loads it from localStorage at init so a
    // toggle set here survives navigation to setup/diag/etc.
    if (window.Icarus && Icarus.devToggles) state.devToggles = Icarus.devToggles;
    const devMap = {
      'dev-burn': ['burn', (on) => 'BURN:' + (on ? 'ON' : 'OFF')],
      'dev-finish': ['finish', (on) => 'FINISH:' + (on ? 'ON' : 'OFF')],
    };
    const applyToggleLabel = (id, key, label) => {
      const b = $(id);
      if (!b) return;
      const on = !!state.devToggles[key];
      b.textContent = label(on);
      b.classList.toggle('on', on);
      if (key === 'finish') { const f = $('finish-run-btn'); if (f) f.textContent = 'FINISH RUN · ' + (on ? 'ON' : 'OFF'); }
    };
    Object.entries(devMap).forEach(([id, [key, label]]) => {
      $(id).addEventListener('click', () => {
        state.devToggles[key] = !state.devToggles[key];
        if (window.Icarus && Icarus.persistToggles) Icarus.persistToggles();
        applyToggleLabel(id, key, label);
        // Burn clocks is a LIVE runner toggle — POST it so a running career picks
        // it up immediately (it's also sent in the start payload for new careers).
        if (key === 'burn') {
          fetch('/api/career/runner/burn_clocks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ burn_clocks: state.devToggles.burn }) }).catch(() => {});
        }
      });
      // Restore the persisted label on load (HTML defaults to OFF).
      applyToggleLabel(id, key, label);
    });
    // BUG #6: LOOP cycles a run-count (1/2/3/5/10/∞) via the shared core helper.
    { const lb = $('dev-loop'); if (lb && window.Icarus && Icarus.loopLabel) {
        const syncLoop = () => { lb.textContent = Icarus.loopLabel(state.devToggles.loopCount); lb.classList.toggle('on', Number(state.devToggles.loopCount) !== 1); };
        lb.addEventListener('click', () => { Icarus.nextLoopCount(); syncLoop(); });
        syncLoop();
      } }
    { const f = $('finish-run-btn'); if (f) f.addEventListener('click', () => $('dev-finish').click()); }


    // not-yet-built tabs: gentle notice (these become real pages next)
    document.querySelectorAll('.tab[data-soon]').forEach((a) => {
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const t = $('tab-live-text');
        const prev = t.textContent;
        t.textContent = a.dataset.soon.toUpperCase() + ' · NEXT';
        setTimeout(() => { t.textContent = prev; }, 1400);
      });
    });
  }

  function setReasonTab(tab) {
    state.reasonTab = tab;
    $('rt-decision').classList.toggle('is-active', tab === 'decision');
    if (state.runner) renderReasoning(state.runner);
  }

  // ---------- boot ----------
  cdInit();   // cool-dash: inject stylesheet (once)
  bind();
  if (window.Icarus && Icarus.bindTheme) Icarus.bindTheme();
  if (window.Icarus && Icarus.wireLogout) Icarus.wireLogout();
  if (window.Icarus && Icarus.ensureAuth) Icarus.ensureAuth();
  if (window.Icarus && Icarus.mountMonitor) Icarus.mountMonitor();
  if (window.Icarus && Icarus.bindDevExtras) Icarus.bindDevExtras();
  syncPortrait();
  loadSelectedTrainee();
  startPolling();
})();
