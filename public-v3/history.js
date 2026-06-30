/* Career History — fetches /api/career/history, renders each completed run as a
   champion profile (final stats, aptitudes, sparks) + full race history.
   Renders an empty state when the backend is unreachable (api() returns null). */
(() => {
  'use strict';
  const I = window.Icarus;
  const { api, fmtCompact, esc, pad2 } = I;
  const $ = (id) => document.getElementById(id);
  const fmtNum = (n) => (n || 0).toLocaleString('en-US');

  // ---- lazy-inject our own stylesheet (mirrors core.js ensureFontLink) -------
  // We own NO html and never touch styles.css; the upgrade styles live in
  // cool-hist.css and are linked once at init.
  function ensureCoolStyles() {
    const id = 'ch-cool-styles';
    if (document.getElementById(id)) return;
    const l = document.createElement('link');
    l.id = id; l.rel = 'stylesheet';
    l.href = 'cool-hist.css?v=2';
    (document.head || document.documentElement).appendChild(l);
  }
  // tag the page root so cool-hist's local --ch-p* place aliases resolve
  function tagCoolRoot() { document.body.classList.add('ch-x'); }

  // honour reduced-motion / coarse-pointer for the heavier effects
  const prefersReducedMotion = () =>
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = () =>
    !window.matchMedia || window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  // place -> palette class shared by ribbon dots + scope (mirrors styles.css .pl-*)
  const placeP = (p) => p === 1 ? 'p1' : p === 2 ? 'p2' : p === 3 ? 'p3' : 'px';

  const gradeBg = (g) => ({ URA: 'bg-amber', WIN: 'bg-green', FAIL: 'bg-red' }[g] || 'bg-mut');

  // ---- final-stat value -> letter grade ------------------------------------
  function statGrade(v) {
    if (v >= 1100) return 'SS';
    if (v >= 1000) return 'A+';
    if (v >= 850)  return 'A';
    if (v >= 800)  return 'B+';
    if (v >= 600)  return 'B';
    if (v >= 500)  return 'C';
    if (v >= 450)  return 'D+';
    if (v >= 350)  return 'D';
    if (v >= 300)  return 'E';
    if (v >= 100)  return 'F';
    return 'G';
  }
  // letter -> tone class (S A B C D E F G)
  const gradeTone = (letter) => {
    const c = (letter || '')[0];
    return c === 'S' ? 'g-s' : c === 'A' ? 'g-a' : c === 'B' ? 'g-b'
         : c === 'C' ? 'g-c' : c === 'D' ? 'g-d' : 'g-g';
  };
  const gradeBadgeCls = (g) => {
    const k = (g || '').toUpperCase();
    if (k === 'CLIMAX') return 'gb-climax';
    if (k === 'G1') return 'gb-g1';
    if (k === 'G2') return 'gb-g2';
    if (k === 'G3') return 'gb-g3';
    return 'gb-op';
  };
  const placeCls = (p) => p === 1 ? 'pl-1' : p === 2 ? 'pl-2' : p === 3 ? 'pl-3' : 'pl-x';
  const placeLbl = (p) => p === 1 ? '1st' : p === 2 ? '2nd' : p === 3 ? '3rd' : (p ? p + 'th' : '—');
  const hpToneCls = (r) => { const f = (r.hp / (r.hpmax || 100)); return f <= 0.18 ? 'hp-red' : f <= 0.42 ? 'hp-amber' : 'hp-green'; };
  const fmtWhen = (ts) => { ts = Number(ts) || 0; if (!ts) return ''; try { return new Date(ts * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; } };
  const MOOD_LBL = { 5: 'Great', 4: 'Good', 3: 'Normal', 2: 'Bad', 1: 'Awful' };
  const moodCls = (m) => m >= 4 ? 'mood-g' : m === 3 ? 'mood-a' : 'mood-r';

  let careers = [];
  let activeIdx = null;

  // ---- profile model -------------------------------------------------------
  // real runs supply `profile`; otherwise derive a plausible one from c.stats.
  function profileFor(c) {
    if (c.profile) return c.profile;
    const st = c.stats || {};
    const fs = [st.speed, st.stamina, st.power, st.guts, st.wit].map((v) => v || 0);
    const sum = fs.reduce((a, b) => a + b, 0);
    const seed = c.index || 1;
    const apt = (i) => ['A', 'B', 'C', 'A', 'B', 'S', 'C', 'D'][(seed + i) % 8];
    // a representative race set derived from the career
    const names = [
      ['G1', 'Arima Kinen', 'Nakayama', 2500, 'Long'], ['G1', 'Japan Cup', 'Tokyo', 2400, 'Medium'],
      ['G1', 'Tenno Sho (Autumn)', 'Tokyo', 2000, 'Medium'], ['G1', 'Osaka Hai', 'Hanshin', 2000, 'Medium'],
      ['G2', 'Kyoto Kinen', 'Kyoto', 2200, 'Medium'], ['G3', 'Aichi Hai', 'Chukyo', 1600, 'Mile'],
    ];
    const wins = c.wins || 0;
    const races = names.map(([grade, name, venue, dist, cat], i) => {
      const f = 1 - i * 0.06;
      return {
        grade, name, venue, surface: 'Turf', dist, cat,
        when: ['Senior Year Late Dec', 'Senior Year Late Nov', 'Senior Year Late Oct', 'Senior Year Early Apr', 'Classic Year Mid Feb', 'Junior Year Late Aug'][i],
        style: 'Late Surger', plan: i % 3 === 0 ? 'mandatory' : 'solver-planned',
        hp: 30 + ((seed * 7 + i * 11) % 50), hpmax: 108,
        spd: Math.round(fs[0] * f), sta: Math.round(fs[1] * f), pwr: Math.round(fs[2] * f),
        gut: Math.round(fs[3] * f), wit: Math.round(fs[4] * f),
        place: i < Math.max(1, Math.round(wins / 4)) ? 1 : (i % 2 ? 2 : 3),
        fans: [30000, 20000, 20000, 12000, 9000, 5000][i],
      };
    });
    return {
      rating: Math.round(sum * 3.1), rank: c.index, career_grade: Math.max(1, Math.min(12, Math.round(sum / 280))),
      date: '—', scenario_label: (c.scenario || 'Trackblazer') + ': Career Complete',
      win_rate: c.races ? Math.round((wins / c.races) * 100) : 0,
      race_fans: Math.round((c.fans_final || 0) * 0.62),
      major_wins: races.filter((r) => r.place === 1).slice(0, 5).map((r) => r.name),
      aptitudes: {
        TRACK: [['Turf', apt(0)], ['Dirt', apt(1)]],
        DISTANCE: [['Sprint', apt(2)], ['Mile', apt(3)], ['Medium', apt(4)], ['Long', apt(5)]],
        STYLE: [['Front', apt(6)], ['Pace', apt(7)], ['Late', apt(0)], ['End', apt(1)]],
      },
      sparks: [['Speed', 3, 12], ['Turf', 2, 5], ['Late Surger', 2, 5], [c.scenario + ' Scenario', 3, 5]],
      races,
    };
  }

  // persistent compare control + instruction banner injected above the list.
  // Always visible (discoverable without a manual); flips to a clear two-pick
  // banner once armed so the user can never lose the thread.
  function ensureCompareBar() {
    let bar = $('ch-cmpbar');
    if (bar) return bar;
    const list = $('ch-list');
    if (!list || !list.parentNode) return null;
    bar = document.createElement('div');
    bar.id = 'ch-cmpbar';
    bar.className = 'ch-cmpbar';
    list.parentNode.insertBefore(bar, list);   // sits between the search box and the list
    return bar;
  }
  function renderCompareBar() {
    const bar = ensureCompareBar();
    if (!bar) return;
    const anchor = careers[activeIdx];
    if (!compareMode) {
      bar.classList.remove('armed');
      bar.innerHTML = careers.length < 2
        ? `<div class="ch-cmp-hint">Run two or more careers to unlock head-to-head compare.</div>`
        : `<button type="button" class="ch-cmp-go" id="ch-cmp-go">&#8644; COMPARE RUNS</button>
           <div class="ch-cmp-hint">Pit this run against another — fans, skills, sparks, win-rate &amp; stats.</div>`;
      const go = $('ch-cmp-go');
      if (go) go.addEventListener('click', () => { compareMode = true; rivalIdx = null; renderCompareBar(); renderList(); });
      return;
    }
    bar.classList.add('armed');
    bar.innerHTML = `
      <div class="ch-cmp-banner">
        <span class="ch-cmp-step">1</span>
        <div class="ch-cmp-txt">
          <div class="ch-cmp-lead">Comparing <b>RUN #${esc(String(anchor ? anchor.index : '—'))}</b>${anchor ? ' · ' + esc((anchor.trainee || '').toUpperCase()) : ''}</div>
          <div class="ch-cmp-sub">&#8595; Now click a <b>second run</b> in the list to see them side-by-side.</div>
        </div>
        <button type="button" class="ch-cmp-cancel" id="ch-cmp-cancel" title="Exit compare mode">CANCEL</button>
      </div>`;
    const cancel = $('ch-cmp-cancel');
    if (cancel) cancel.addEventListener('click', () => { compareMode = false; rivalIdx = null; renderCompareBar(); renderList(); });
  }

  function renderList() {
    const host = $('ch-list');
    $('ch-count').textContent = careers.length;
    renderCompareBar();
    host.classList.toggle('ch-picking', compareMode);
    host.innerHTML = '';
    careers.forEach((c, i) => {
      const isAnchor = i === activeIdx;
      const isRival = compareMode && i === rivalIdx;
      const isPickable = compareMode && !isAnchor;
      const row = document.createElement('div');
      // rarity edge seeded by rank (ch-rar) + compare states
      row.className = 'listrow ch-rar'
        + (isAnchor ? ' is-active' : '')
        + (isRival ? ' ch-rival' : '')
        + (compareMode && isAnchor ? ' ch-anchor' : '')
        + (isPickable ? ' ch-pickable' : '');
      row.style.setProperty('--rar', rarityColor(c.career_rank || c.grade));
      // compare-mode tags: the anchor is labelled, every OTHER run shows a big
      // "CLICK TO COMPARE" affordance over the whole row.
      const tag = compareMode
        ? (isAnchor
            ? `<span class="ch-row-tag anchor">RUN A</span>`
            : `<span class="ch-row-tag pick">${isRival ? '✓ COMPARED' : 'CLICK TO COMPARE'}</span>`)
        : '';
      row.innerHTML = `
        <div class="listrow-top">
          <span class="listrow-title">RUN #${c.index} · ${esc((c.trainee || '').toUpperCase())}</span>
          <span class="listrow-right">
            ${tag}
            <span class="tagbadge ${gradeBg(c.grade || c.career_rank)}">${esc(c.grade || c.career_rank || '—')}</span>
            ${c.run_id ? `<a class="rowlog" href="logview.html?run_id=${encodeURIComponent(c.run_id)}" target="_blank" rel="noopener" title="Open this run's full log" onclick="event.stopPropagation()">📋</a>` : ''}
          </span>
        </div>
        <div class="listrow-meta">${esc(c.scenario || 'Trackblazer')} · ${c.turn || 0} turns${c.runtime ? ' · ' + esc(c.runtime) : ''}${c.finished_at ? ' · ' + esc(fmtWhen(c.finished_at)) : ''}</div>
        <div class="listrow-kv">
          <span class="mut">FANS <span class="${isAnchor ? 'c-amber' : 'c-mut'}">${fmtCompact(c.fans_final)}</span></span>
          <span class="mut">RACES <span class="c-mut">${c.races || 0}</span></span>
          <span class="mut">WINS <span class="${(c.wins >= 18) ? 'c-green' : 'c-mut'}">${c.wins || 0}</span></span>
        </div>`;
      row.addEventListener('click', () => {
        if (compareMode && isPickable) {
          // STEP 2: pick this run as the rival and open the VS overlay
          rivalIdx = i;
          renderList();
          openCompareModal(careers[activeIdx], careers[i]);
        } else if (compareMode && isAnchor) {
          // clicking the anchor again is a no-op (it's already RUN A)
        } else {
          activeIdx = i; renderList(); renderReport();
        }
      });
      host.appendChild(row);
    });
  }

  function aptSetHtml(pairs) {
    return pairs.map(([k, g]) =>
      `<span class="aptchip">${esc(k)}<b class="${gradeTone(g)}">${esc(g)}</b></span>`).join('');
  }

  function raceRowHtml(r, idx) {
    const venue = r.venue ? esc(r.venue) + ' · ' : '';
    const hasField = !!(r.field && r.field.length);
    const replayBtn = hasField
      ? `<button type="button" class="ch-replay-btn" data-replay="${idx}" title="Replay this race as an animated flight recorder">&#9654; REPLAY</button>`
      : '';
    return `
      <div class="racerow${r.place === 1 ? ' win' : ''}">
        <div class="gradebadge ${gradeBadgeCls(r.grade)}">${esc(r.grade)}</div>
        <div>
          <div class="race-name">${esc(r.name)}</div>
          <div class="race-dist">${venue}${esc(r.surface)} ${r.dist}m <span style="color:var(--label)">(${esc(r.cat)})</span></div>
          <div class="race-meta">${esc(r.when)} · ${esc(r.style)} · <span class="plan">${esc(r.plan)}</span></div>
          <div class="race-stats">${r.mood ? `<span class="moodbadge ${moodCls(r.mood)}">${esc(MOOD_LBL[r.mood] || ('Mood ' + r.mood))}</span>` : ''}<span class="hpbadge ${hpToneCls(r)}">HP ${r.hp}/${r.hpmax}</span>SPD ${r.spd} · STA ${r.sta} · PWR ${r.pwr} · GUT ${r.gut} · WIT ${r.wit}</div>
          ${forecastGaugeHtml(r)}
        </div>
        <div class="race-right">
          <span class="placebadge ${placeCls(r.place)}">${placeLbl(r.place)}</span>
          ${winprobChip(r)}
          ${scopeHtml(r, { small: true })}
          ${replayBtn}
          <span class="race-fans">${fmtNum(r.fans)} fans</span>
        </div>
      </div>`;
  }

  // ---- real-data adapters (prefer the backend's per-career fields; the mock
  //      profileFor() is only a fallback for older/partial history rows) --------
  // Sparks: backend sends objects {name, stars, initial_points}; mock sends [name,stars,pts] tuples.
  function sparkTuples(c, p) {
    if (c.sparks && c.sparks.length) {
      return c.sparks.map((s) => Array.isArray(s)
        ? s
        : [s.name || s.label || 'Spark', Number(s.stars || s.star || 0), Number(s.initial_points ?? s.points ?? s.pts ?? 0)]);
    }
    return p.sparks || [];
  }
  // Aptitudes: backend sends {track:{turf,dirt}, distance:{...}, style:{...}}; render wants
  // {TRACK:[[k,g]], DISTANCE:[...], STYLE:[...]}.
  function aptFromBackend(c) {
    const a = c.aptitudes;
    if (!a || !a.distance) return null;
    const U = (s) => String(s == null ? '' : s).toUpperCase();
    return {
      TRACK: [['Turf', U(a.track && a.track.turf)], ['Dirt', U(a.track && a.track.dirt)]],
      DISTANCE: [['Sprint', U(a.distance.sprint)], ['Mile', U(a.distance.mile)], ['Medium', U(a.distance.medium)], ['Long', U(a.distance.long)]],
      STYLE: [['Front', U(a.style && a.style.front)], ['Pace', U(a.style && a.style.pace)], ['Late', U(a.style && a.style.late)], ['End', U(a.style && a.style.end)]],
    };
  }
  // Real race row (runner _race_program_summary shape) -> raceRowHtml shape.
  function adaptRace(r) {
    const rank = Number(r.final_rank ?? r.rank ?? 0);
    const st = r.stat_snapshot || {};
    const md = r.master_metadata || {};
    return {
      grade: r.grade || '',
      name: r.name || ('Race ' + (r.program_id || '')),
      venue: md.venue || r.venue || '',
      surface: r.terrain || r.surface || '',
      dist: r.distance_m || r.dist || '',
      cat: r.distance_type || r.cat || '',
      when: md.date || (r.turn ? 'Turn ' + r.turn : ''),
      style: r.running_style || (r.style_adaptation && r.style_adaptation.base_user_style) || '',
      plan: r.race_type || 'race',
      hp: Number(st.hp ?? st.vital ?? 0), hpmax: Number(st.max_hp ?? st.max_vital ?? 100),
      spd: Number(st.speed ?? 0), sta: Number(st.stamina ?? 0), pwr: Number(st.power ?? 0),
      gut: Number(st.guts ?? 0), wit: Number(st.wit ?? st.wiz ?? 0),
      place: (rank > 0 && rank < 90) ? rank : 0,
      fans: Number(r.fans ?? 0),
      mood: Number(st.motivation ?? st.mood ?? 0),
      winprob: r.win_probability || null,   // read-only pre-race estimate (may be null/unavailable)
      field: Array.isArray(r.field_results) ? r.field_results : null,  // per-horse finish (for the replay)
      turn: Number(r.turn || 0),
    };
  }

  // Pre-race win-probability chip (read-only). Hidden when no named-rival field
  // was known for the race, so it never shows a misleading 100%.
  function winprobChip(r) {
    const w = r.winprob;
    if (!w || !w.available || w.p_win == null) return '';
    const pct = Math.round(w.p_win * 100);
    const top3 = Math.round((w.p_top3 || 0) * 100);
    const tone = pct >= 50 ? 'c-green' : pct >= 20 ? 'c-amber' : 'c-mut';
    // "~" marks this as a PRELIMINARY, uncalibrated estimate (default logistic
    // scale, pending backtest calibration). It is computed vs the NAMED rivals
    // only — the full starting gate is larger — so it is an optimistic upper bound.
    return `<span class="winprob ${tone}" style="font-size:var(--fs-md);font-weight:600" `
      + `title="Preliminary (uncalibrated) pre-race estimate vs the ${(w.field_size || 1) - 1} named rival(s) only — the full gate is larger, so this is optimistic. Top-3 ~${top3}%. Read-only, does not affect play.">`
      + `~P(win) ${pct}%</span>`;
  }

  // ==========================================================================
  //  CAREER-HISTORY UPGRADES  (additive: heatmap, trace, holo, compare, scope)
  // ==========================================================================

  // ---- shared per-turn model -------------------------------------------------
  // Build a turn -> {race, place, win, placed, skills} map from c.race_results,
  // plus a best-effort stat-gain intensity per turn when consecutive snapshots
  // are available (race rows carry stat_snapshot; the delta is a coarse proxy).
  function turnModel(c) {
    const races = (c.race_results || []).map(adaptRace).map((r, i) => {
      r._turn = Number((c.race_results[i] && c.race_results[i].turn) || 0);
      r._snap = (c.race_results[i] && c.race_results[i].stat_snapshot) || null;
      r._skills = (c.race_results[i] && (c.race_results[i].skills || c.race_results[i].skills_bought)) || null;
      return r;
    });
    const byTurn = {};
    // stat-gain intensity: total-stats delta between consecutive race snapshots,
    // spread evenly is impossible (we only see race turns), so we colour the race
    // turn by its own snapshot magnitude vs the career max. Training-only turns
    // have no snapshot here -> rendered as faint accent cells (documented).
    const totals = races.map((r) => (r.spd || 0) + (r.sta || 0) + (r.pwr || 0) + (r.gut || 0) + (r.wit || 0));
    const maxTotal = Math.max(1, ...totals);
    races.forEach((r, i) => {
      const t = r._turn; if (!t) return;
      const place = r.place || 0;
      byTurn[t] = {
        race: r, place,
        win: place === 1, placed: place >= 2 && place <= 3, ran: place > 3,
        intensity: Math.round((totals[i] / maxTotal) * 4),
        hasSkill: !!(r._skills && r._skills.length),
        name: r.name,
      };
    });
    return { byTurn, races, hasIntensity: races.some((r) => r._snap) };
  }

  // year/turn labels: 78 turns = 3 years x 26 columns (Junior/Classic/Senior)
  const YEARS = ['JUNIOR', 'CLASSIC', 'SENIOR'];
  const monthForCol = (col) => {
    // 26 cols ≈ 2 per month (Early/Late) starting Jan; col 0-based
    const M = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const half = col % 2 === 0 ? 'Early' : 'Late';
    return half + ' ' + M[Math.min(11, Math.floor(col / 2))];
  };

  // ---- 1) 78-TURN HEATMAP ----------------------------------------------------
  function heatmapHtml(c) {
    const m = turnModel(c);
    let rows = '';
    for (let y = 0; y < 3; y++) {
      let cells = '';
      for (let col = 0; col < 26; col++) {
        const turn = y * 26 + col + 1;          // 1..78
        const info = m.byTurn[turn];
        let cls = 'ch-cell', tip = '';
        if (info) {
          if (info.win) { cls += ' is-win'; }
          else if (info.placed) { cls += ' is-placed'; }
          else if (info.ran) { cls += ' is-ran'; }
          if (m.hasIntensity && info.intensity > 0 && !info.win && !info.placed && !info.ran) cls += ' t' + info.intensity;
          if (info.hasSkill) cls += ' has-skill';
          const outcome = info.win ? '<span class="win">WON</span>' : info.placed ? '<span class="placed">placed ' + placeLbl(info.place) + '</span>' : info.ran ? '<span class="ran">' + placeLbl(info.place) + '</span>' : 'raced';
          tip = '<b>Turn ' + turn + '</b> · ' + esc(YEARS[y]) + ' ' + esc(monthForCol(col)) + '<br>' + esc(info.name || 'Race') + ' — ' + outcome + (info.hasSkill ? '<br>★ skill purchased' : '');
        } else {
          // no race this turn -> faint training/accent cell (limitation: per-turn
          // training detail isn't in history rows, only race_results).
          cls += ' is-empty is-train';
          tip = '<b>Turn ' + turn + '</b> · ' + esc(YEARS[y]) + ' ' + esc(monthForCol(col)) + '<br>training / no race recorded';
        }
        cells += '<div class="' + cls + '" data-tip="' + esc(tip) + '"></div>';
      }
      rows += '<div class="ch-heat-yr"><div class="ch-heat-yk">' + YEARS[y] + '</div><div class="ch-heat-cells">' + cells + '</div></div>';
    }
    const note = m.hasIntensity
      ? 'race turns coloured by result; training turns by stat intensity'
      : 'race turns coloured by result; training turns shown faint (per-turn training detail unavailable)';
    return `
      <div class="ch-sec">
        <div class="ch-sec-hd"><span class="ch-sec-t">CAREER HEATMAP</span><span class="ch-sec-spacer"></span><span class="ch-sec-note">${esc(note)}</span></div>
        <div class="ch-heat">${rows}</div>
        <div class="ch-heat-legend">
          <span><i class="lg-win"></i>win</span>
          <span><i class="lg-placed"></i>placed</span>
          <span><i class="lg-ran"></i>also-ran</span>
          <span><i class="lg-train"></i>training</span>
          <span><i class="lg-skill">★</i>skill buy</span>
        </div>
      </div>`;
  }

  // shared floating tooltip for heatmap cells
  let chTip = null;
  function ensureTip() {
    if (chTip) return chTip;
    chTip = document.createElement('div');
    chTip.className = 'ch-tip';
    document.body.appendChild(chTip);
    return chTip;
  }
  function wireHeatTips(root) {
    const tip = ensureTip();
    root.querySelectorAll('.ch-cell[data-tip]').forEach((cell) => {
      cell.addEventListener('mouseenter', () => { tip.innerHTML = cell.dataset.tip; tip.classList.add('show'); });
      cell.addEventListener('mousemove', (e) => {
        let x = e.clientX + 14, y = e.clientY + 14;
        const w = tip.offsetWidth || 200, h = tip.offsetHeight || 40;
        if (x + w > window.innerWidth - 8) x = e.clientX - w - 14;
        if (y + h > window.innerHeight - 8) y = e.clientY - h - 14;
        tip.style.left = x + 'px'; tip.style.top = y + 'px';
      });
      cell.addEventListener('mouseleave', () => tip.classList.remove('show'));
    });
  }

  // ---- 2) RACE TRACE RIBBON --------------------------------------------------
  function traceHtml(c) {
    const m = turnModel(c);
    const races = m.races.filter((r) => r._turn).sort((a, b) => a._turn - b._turn);
    if (!races.length) return '';
    const W = 760, H = 150, padL = 30, padR = 12, padT = 14, padB = 22;
    const innerW = W - padL - padR, innerH = H - padT - padB;
    // y maps finishing place: 1st at top rail, worse dips lower. Clamp to 1..maxRail.
    const maxRail = Math.max(8, ...races.map((r) => (r.place > 0 ? r.place : 0)));
    const yFor = (place) => {
      if (!place || place < 1) return padT + innerH;          // unknown -> bottom
      const f = (place - 1) / Math.max(1, maxRail - 1);
      return padT + f * innerH;
    };
    const xFor = (i) => padL + (races.length === 1 ? innerW / 2 : (i / (races.length - 1)) * innerW);
    // faint grade reference rails (1st / 3rd)
    let grid = '';
    [[1, '1st'], [3, '3rd'], [maxRail, placeLbl(maxRail)]].forEach(([p, lbl]) => {
      const y = yFor(p).toFixed(1);
      grid += `<line class="tr-grid" x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}"/>`;
      grid += `<text class="tr-grid-lbl" x="2" y="${(Number(y) + 3).toFixed(1)}">${esc(String(lbl))}</text>`;
    });
    const pts = races.map((r, i) => `${xFor(i).toFixed(1)},${yFor(r.place).toFixed(1)}`);
    const line = pts.join(' ');
    const area = `M${xFor(0).toFixed(1)},${(padT + innerH).toFixed(1)} L${line.replace(/ /g, ' L')} L${xFor(races.length - 1).toFixed(1)},${(padT + innerH).toFixed(1)} Z`;
    const dots = races.map((r, i) => {
      const cx = xFor(i).toFixed(1), cy = yFor(r.place).toFixed(1);
      const t = `T${r._turn} · ${esc(r.name || 'Race')} · ${placeLbl(r.place)}`;
      return `<circle class="tr-dot ${placeP(r.place)}" cx="${cx}" cy="${cy}" r="3.6"><title>${t}</title></circle>`;
    }).join('');
    const animate = prefersReducedMotion() ? '' : ' animate';
    return `
      <div class="ch-sec">
        <div class="ch-sec-hd"><span class="ch-sec-t">RACE TRACE</span><span class="ch-sec-spacer"></span><span class="ch-sec-note">${races.length} races · finishing place over time</span></div>
        <div class="ch-trace">
          <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="finishing place over the career">
            ${grid}
            <path class="tr-area" d="${area}"/>
            <polyline class="tr-line${animate}" points="${line}" pathLength="1000" style="--tr-len:1000"/>
            ${dots}
          </svg>
          <div class="ch-trace-foot">
            <span><i class="p1"></i>1st</span><span><i class="p2"></i>2nd</span>
            <span><i class="p3"></i>3rd</span><span><i class="px"></i>4th+</span>
          </div>
        </div>
      </div>`;
  }

  // ---- 3) HOLO TRAINEE CARD --------------------------------------------------
  // rarity tint seeded by career_rank (SS/S → amber-gold, A → cyan, B → green …)
  function rarityColor(rank) {
    const r = String(rank || '').toUpperCase();
    if (r[0] === 'S') return 'var(--amber)';
    if (r[0] === 'A') return '#5fd6e0';
    if (r[0] === 'B') return 'var(--green)';
    if (r[0] === 'C') return '#6f9be0';
    if (r[0] === 'D') return 'var(--purple)';
    return 'var(--line-card)';
  }
  // attach holo foil + pointer-tilt to the profile avatar after render
  function wireHolo(host, rank) {
    const av = host.querySelector('.prof-av');
    if (!av) return;
    av.classList.add('ch-holo');
    av.style.setProperty('--rar', rarityColor(rank));
    // foil + glare layers + rarity tag
    const foil = document.createElement('span'); foil.className = 'ch-foil';
    const glare = document.createElement('span'); glare.className = 'ch-glare';
    const tag = document.createElement('span'); tag.className = 'ch-rar-tag'; tag.textContent = String(rank || '—');
    av.appendChild(foil); av.appendChild(glare); av.appendChild(tag);
    if (prefersReducedMotion() || !finePointer()) return;   // static flat card
    const onMove = (e) => {
      const r = av.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;
      const py = (e.clientY - r.top) / r.height;
      av.classList.add('tilt');
      av.style.setProperty('--foil-x', (px * 100).toFixed(1) + '%');
      av.style.setProperty('--foil-y', (py * 100).toFixed(1) + '%');
      av.style.setProperty('--foil-a', (90 + px * 180).toFixed(0) + 'deg');
      const rx = (0.5 - py) * 8, ry = (px - 0.5) * 8;
      av.style.transform = `perspective(520px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg)`;
    };
    const onLeave = () => { av.classList.remove('tilt'); av.style.transform = ''; };
    av.addEventListener('pointermove', onMove);
    av.addEventListener('pointerleave', onLeave);
  }

  // ---- 1b) FINAL-STATS ATTRIBUTE RADAR (toggle beside the bars) -------------
  // The same pentagon idea as the VS radar, but for a SINGLE career's 5 stats.
  // Per-career stat TARGETS are not stored, so we draw a faint "cap reference"
  // pentagon at STAT_CAP_REF behind the real polygon (a HONEST reference, not a
  // faked goal) plus a tiny legend. Scaled against the global 1200 cap so the
  // shape reads as "how close to maxed" rather than against an invented target.
  const STAT_CAP = 1200;        // Trackblazer global per-stat cap (see memory)
  const STAT_CAP_REF = 1100;    // faint reference ring (≈ a strong build), NOT a target
  const STAT_AXES = [['SPD', 'speed'], ['STA', 'stamina'], ['POW', 'power'], ['GUT', 'guts'], ['WIT', 'wit']];

  function statRadarSvg(st) {
    const W = 260, cx = W / 2, cy = W / 2 + 4, R = 86, n = STAT_AXES.length;
    const ang = (i) => (-Math.PI / 2) + (i / n) * Math.PI * 2;
    const ptsAt = (frac, fn) => STAT_AXES.map((_, i) => {
      const f = (typeof frac === 'function') ? frac(i) : frac;
      return `${(cx + Math.cos(ang(i)) * R * f).toFixed(1)},${(cy + Math.sin(ang(i)) * R * f).toFixed(1)}`;
    }).join(' ');
    // concentric grid rings (25/50/75/100% of the cap)
    let grid = '';
    [0.25, 0.5, 0.75, 1].forEach((g) => { grid += `<polygon class="rd-grid" points="${ptsAt(g)}"/>`; });
    // faint CAP-REFERENCE pentagon (honest: ~1100/1200, drawn behind the fill)
    const capFrac = STAT_CAP_REF / STAT_CAP;
    const capPoly = `<polygon class="rd-cap" points="${ptsAt(capFrac)}"/>`;
    // axes + labels + per-stat value
    let axes = '', labels = '';
    STAT_AXES.forEach(([lbl, key], i) => {
      const x = cx + Math.cos(ang(i)) * R, y = cy + Math.sin(ang(i)) * R;
      axes += `<line class="rd-axis" x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/>`;
      const lx = cx + Math.cos(ang(i)) * (R + 18), ly = cy + Math.sin(ang(i)) * (R + 18);
      const anchor = Math.abs(Math.cos(ang(i))) < 0.3 ? 'middle' : (Math.cos(ang(i)) > 0 ? 'start' : 'end');
      const v = Number(st[key] || 0);
      const g = statGrade(v);
      labels += `<text class="rd-lbl" x="${lx.toFixed(1)}" y="${(ly - 1).toFixed(1)}" text-anchor="${anchor}">${esc(lbl)}</text>`;
      labels += `<text class="rd-val ${gradeTone(g)}" x="${lx.toFixed(1)}" y="${(ly + 11).toFixed(1)}" text-anchor="${anchor}">${v}</text>`;
    });
    // the real attribute polygon (clamped 0..1 against the global cap)
    const poly = STAT_AXES.map(([, key], i) => {
      const v = Math.max(0.015, Math.min(1, Number(st[key] || 0) / STAT_CAP));
      return `${(cx + Math.cos(ang(i)) * R * v).toFixed(1)},${(cy + Math.sin(ang(i)) * R * v).toFixed(1)}`;
    }).join(' ');
    return `<svg viewBox="0 0 ${W} ${W}" role="img" aria-label="attribute radar of the five final stats">`
      + `${grid}${capPoly}${axes}<polygon class="rd-poly" points="${poly}"/>${labels}</svg>`;
  }

  // the FINAL STATS block: bars (default) + radar, swapped by a tiny toggle.
  function finalStatsHtml(st, FS) {
    const barsHtml = `
      <div class="fstats">
        ${FS.map(([k, v]) => { const g = statGrade(v || 0); return `
          <div class="fstat"><div class="fstat-k">${k}</div><div class="fstat-g ${gradeTone(g)}">${g}</div><div class="fstat-v">${v || 0}</div></div>`; }).join('')}
      </div>`;
    return `
      <div class="prof-sec-t fs-head">
        <span>FINAL STATS</span>
        <span class="fs-toggle" role="tablist" aria-label="final stats view">
          <button type="button" class="fs-tab is-on" data-fsview="bars" role="tab" aria-selected="true">BARS</button>
          <button type="button" class="fs-tab" data-fsview="radar" role="tab" aria-selected="false">RADAR</button>
        </span>
      </div>
      <div class="fs-view fs-bars">${barsHtml}</div>
      <div class="fs-view fs-radar" hidden>
        <div class="ch-statradar">${statRadarSvg(st)}</div>
        <div class="ch-statradar-lg">
          <span><i class="lg-poly"></i>final stats</span>
          <span><i class="lg-cap"></i>cap reference (~${STAT_CAP_REF}/${STAT_CAP}, not a target)</span>
        </div>
      </div>`;
  }
  // wire the bars/radar tabs after render (scoped to the host)
  function wireStatToggle(host) {
    const tabs = host.querySelectorAll('.fs-tab');
    const bars = host.querySelector('.fs-view.fs-bars');
    const radar = host.querySelector('.fs-view.fs-radar');
    if (!tabs.length || !bars || !radar) return;
    tabs.forEach((t) => t.addEventListener('click', () => {
      const view = t.dataset.fsview;
      tabs.forEach((x) => { const on = x === t; x.classList.toggle('is-on', on); x.setAttribute('aria-selected', on ? 'true' : 'false'); });
      const showRadar = view === 'radar';
      radar.hidden = !showRadar; bars.hidden = showRadar;
    }));
  }

  // ---- 5) WIN-PROBABILITY RADAR SCOPE ---------------------------------------
  // small CSS scope for a race that has win_probability.available. Trainee is the
  // bright centre pip; rivals are outer blips spaced round the ring; centre shows
  // ~P(win)%. Returns '' when no winprob data so race rows stay clean.
  function scopeHtml(r, opts) {
    const w = r.winprob;
    if (!w || !w.available || w.p_win == null) return '';
    const pct = Math.round(w.p_win * 100);
    const field = Math.max(1, Number(w.field_size || 1));
    const rivals = Math.max(0, field - 1);
    const cls = pct >= 50 ? '' : pct >= 20 ? ' lowp' : ' weakp';
    const sm = (opts && opts.small) ? ' sm' : '';
    // rivals on a ring; closer/brighter rivals = stronger field (just visual)
    let blips = '';
    const N = Math.min(12, rivals);
    for (let i = 0; i < N; i++) {
      const ang = (i / N) * Math.PI * 2 + 0.5;
      const rad = 30 + ((i * 37) % 14);            // % from centre, lightly varied
      const x = 50 + Math.cos(ang) * rad * 0.7;
      const y = 50 + Math.sin(ang) * rad * 0.7;
      blips += `<span class="sc-blip" style="left:${x.toFixed(1)}%;top:${y.toFixed(1)}%"></span>`;
    }
    const top3 = Math.round((w.p_top3 || 0) * 100);
    const title = `Preliminary win-probability scope vs ${rivals} named rival(s). ~P(win) ${pct}% · top-3 ~${top3}%. Read-only estimate.`;
    return `
      <div class="ch-scope${sm}${cls}" title="${esc(title)}">
        <span class="sc-ring" style="width:80%;height:80%"></span>
        <span class="sc-ring" style="width:52%;height:52%"></span>
        <span class="sc-ring" style="width:26%;height:26%"></span>
        <span class="sc-cross h"></span><span class="sc-cross v"></span>
        <span class="sc-sweep"></span>
        ${blips}
        <span class="sc-pip"></span>
        <span class="sc-read">${pct}%</span>
      </div>`;
  }

  // ==========================================================================
  //  3b) FORECAST → ACTUAL  (is the win-prob model earning my trust?)
  // ==========================================================================
  // For a race that HAS win_probability.available we show the predicted ~P(win)%
  // as a bar, then overlay the ACTUAL finishing place as a hit/miss marker:
  //   • predicted high & won  -> HIT (the model called it)
  //   • predicted low  & won  -> UPSET (the field surprised the model)
  //   • predicted high & lost -> MISS (the model over-promised)
  //   • predicted low  & lost -> as-expected
  const HI_CONF = 0.5;   // "high confidence" threshold for the calibration read
  function forecastVerdict(r) {
    const w = r.winprob;
    if (!w || !w.available || w.p_win == null || !r.place) return null;
    const p = Math.max(0, Math.min(1, w.p_win));
    const won = r.place === 1;
    const top3 = r.place >= 1 && r.place <= 3;
    let kind, lbl, tone;
    if (won && p >= HI_CONF) { kind = 'hit'; lbl = 'HIT'; tone = 'c-green'; }
    else if (won && p < 0.2) { kind = 'upset'; lbl = 'UPSET'; tone = 'c-cyan'; }
    else if (won) { kind = 'hit'; lbl = 'WON'; tone = 'c-green'; }
    else if (!top3 && p >= HI_CONF) { kind = 'miss'; lbl = 'MISS'; tone = 'c-red'; }
    else if (top3 && p >= HI_CONF) { kind = 'near'; lbl = 'NEAR'; tone = 'c-amber'; }
    else { kind = 'ok'; lbl = 'AS EXPECTED'; tone = 'c-mut'; }
    return { p, won, top3, kind, lbl, tone, pct: Math.round(p * 100), place: r.place };
  }
  // small per-row gauge: predicted bar + actual-finish marker + verdict tag
  function forecastGaugeHtml(r) {
    const v = forecastVerdict(r);
    if (!v) return '';
    // the actual-finish marker position: 1st sits at the far-right (best), worse
    // finishes slide left, so a HIT lands the marker over the high predicted fill.
    const fieldSize = Math.max(2, Number((r.winprob && r.winprob.field_size) || 8));
    const actualFrac = Math.max(0, Math.min(1, 1 - (v.place - 1) / Math.max(1, fieldSize - 1)));
    const fillTone = v.pct >= 50 ? 'g' : v.pct >= 20 ? 'a' : 'r';
    return `
      <div class="ch-fc" title="Predicted ~P(win) ${v.pct}% vs the named field; finished ${esc(placeLbl(v.place))}. ${esc(v.lbl)}. Preliminary, read-only.">
        <span class="ch-fc-k">FORECAST</span>
        <span class="ch-fc-track">
          <span class="ch-fc-fill ${fillTone}" style="width:${v.pct}%"></span>
          <span class="ch-fc-pred" style="left:${v.pct}%"></span>
          <span class="ch-fc-actual ${v.kind}" style="left:${(actualFrac * 100).toFixed(1)}%" title="finished ${esc(placeLbl(v.place))}">${esc(placeLbl(v.place))}</span>
        </span>
        <span class="ch-fc-pct">${v.pct}%</span>
        <span class="ch-fc-tag ${v.tone}">${esc(v.lbl)}</span>
      </div>`;
  }
  // running calibration read across the career's forecasted races:
  // of the HIGH-confidence (≥HI_CONF) races, how often did the trainee actually win?
  function calibrationHtml(races) {
    const fc = races.map(forecastVerdict).filter(Boolean);
    if (!fc.length) return '';
    const hi = fc.filter((v) => v.p >= HI_CONF);
    const hiWon = hi.filter((v) => v.won).length;
    const upsets = fc.filter((v) => v.kind === 'upset').length;
    const misses = fc.filter((v) => v.kind === 'miss').length;
    // last-N strip of verdict pips (most-recent on the right)
    const N = Math.min(16, fc.length);
    const recent = fc.slice(-N);
    const pips = recent.map((v) =>
      `<span class="ch-cal-pip ${v.kind}" title="~P(win) ${v.pct}% → ${esc(placeLbl(v.place))} · ${esc(v.lbl)}"></span>`).join('');
    const hiRate = hi.length ? Math.round((hiWon / hi.length) * 100) : null;
    const rateTone = hiRate == null ? 'c-mut' : hiRate >= 60 ? 'c-green' : hiRate >= 35 ? 'c-amber' : 'c-red';
    const verdict = hi.length < 3
      ? 'too few high-confidence races to judge yet'
      : hiRate >= 60 ? 'model is calling favourites well'
      : hiRate >= 35 ? 'model is roughly honest on favourites'
      : 'model is over-confident on its favourites';
    return `
      <div class="ch-cal">
        <div class="ch-cal-hd">
          <span class="ch-cal-t">FORECAST CALIBRATION</span>
          <span class="ch-cal-sub">is the win-prob model earning trust?</span>
        </div>
        <div class="ch-cal-body">
          <div class="ch-cal-stat">
            <div class="ch-cal-v ${rateTone}">${hiRate == null ? '—' : hiRate + '%'}</div>
            <div class="ch-cal-k">high-conf wins<br>(${hiWon}/${hi.length} at ≥${Math.round(HI_CONF * 100)}%)</div>
          </div>
          <div class="ch-cal-stat"><div class="ch-cal-v c-cyan">${upsets}</div><div class="ch-cal-k">upsets<br>(won as longshot)</div></div>
          <div class="ch-cal-stat"><div class="ch-cal-v c-red">${misses}</div><div class="ch-cal-k">misses<br>(favourite flopped)</div></div>
          <div class="ch-cal-strip">
            <div class="ch-cal-strip-k">last ${N} forecasts</div>
            <div class="ch-cal-pips">${pips}</div>
          </div>
        </div>
        <div class="ch-cal-note">${esc(verdict)} · preliminary, read-only estimates vs the named field only</div>
      </div>`;
  }

  // ==========================================================================
  //  2b) RACE REPLAY  (self-contained flight recorder — no logview dependency)
  // ==========================================================================
  // Build per-horse lanes from field_results, animate left→right ordered by
  // finish_order, freeze into a 1st/2nd/3rd podium. Reduced-motion jumps to the
  // final podium. Opens inside Icarus.modal so it themes + closes like the rest.
  const STYLE_LBL = { 1: 'Front', 2: 'Pace', 3: 'Late', 4: 'End' };
  function styleName(s) {
    if (s == null || s === '') return '';
    const n = Number(s);
    if (!Number.isNaN(n) && STYLE_LBL[n]) return STYLE_LBL[n];
    return String(s);
  }
  function openReplayModal(r) {
    const field = (r.field || []).slice();
    if (!field.length) {
      I.modal({ title: 'RACE REPLAY', sub: esc(r.name || 'race'), body:
        `<div class="ch-rp-empty">No field-results were recorded for this race, so it can&rsquo;t be replayed. (Replays need the per-horse finish data that newer runs capture.)</div>` });
      return;
    }
    // normalise + order by finish_order (fallback: keep given order)
    const lanes = field.map((f, i) => {
      const order = Number(f.finish_order ?? f.finish ?? (i + 1)) || (i + 1);
      return {
        order,
        isPlayer: !!f.is_player,
        style: styleName(f.running_style),
        chara: f.chara_id != null ? String(f.chara_id) : '',
        time: Number(f.finish_time || 0),
        diff: Number(f.finish_diff_time || 0),
      };
    }).sort((a, b) => a.order - b.order);
    const n = lanes.length;
    // name each lane (the player is named; rivals are anonymised blips)
    lanes.forEach((l, i) => {
      l.name = l.isPlayer ? (r._trainee || 'YOU') : ('Rival ' + (l.chara || (i + 1)));
      l.podium = l.order <= 3 ? l.order : 0;
    });
    const podiumOf = (o) => o === 1 ? '1st' : o === 2 ? '2nd' : o === 3 ? '3rd' : o + 'th';
    // lane rows: a track with a runner chip that we animate to a finish offset.
    // finish x is staggered by finish_order so the pack visibly strings out.
    const laneRows = lanes.map((l, i) => {
      // winner reaches ~96%, each subsequent place backs off a touch (visual)
      const fx = 96 - (l.order - 1) * Math.min(8, 70 / Math.max(1, n - 1));
      const cls = l.isPlayer ? ' is-player' : '';
      const sub = (l.diff && l.order > 1) ? `+${l.diff.toFixed(2)}s` : (l.time ? l.time.toFixed(2) + 's' : '');
      return `
        <div class="ch-rp-lane${cls}" style="--fx:${fx.toFixed(1)}%;--i:${i}">
          <div class="ch-rp-lane-k">${esc(podiumOf(l.order))}</div>
          <div class="ch-rp-track">
            <div class="ch-rp-runner ${l.podium ? 'pod' + l.podium : ''}">
              <span class="ch-rp-chip">${l.isPlayer ? '★' : ''}</span>
              <span class="ch-rp-name">${esc(l.name)}${l.style ? ` <i>${esc(l.style)}</i>` : ''}</span>
            </div>
          </div>
          <div class="ch-rp-fin">${esc(sub)}</div>
        </div>`;
    }).join('');
    // a small podium freeze-frame (top 3)
    const top3 = lanes.filter((l) => l.podium).sort((a, b) => a.order - b.order);
    const podiumHtml = top3.map((l) =>
      `<div class="ch-rp-pod p${l.order}${l.isPlayer ? ' is-player' : ''}">
         <div class="ch-rp-pod-medal">${l.order === 1 ? '\u{1F947}' : l.order === 2 ? '\u{1F948}' : '\u{1F949}'}</div>
         <div class="ch-rp-pod-name">${esc(l.name)}</div>
         <div class="ch-rp-pod-block">${esc(podiumOf(l.order))}</div>
       </div>`).join('');
    const reduced = prefersReducedMotion();
    const body = `
      <div class="ch-rp${reduced ? ' reduced' : ''}">
        <div class="ch-rp-hd">
          <span class="ch-rp-meta">${esc(r.grade || '')} · ${esc(r.name || 'Race')} · ${esc(r.surface || '')} ${r.dist || ''}m · ${n} runners</span>
          <button type="button" class="ch-rp-play" data-rp-play>${reduced ? '▶ PLAY' : '↺ REPLAY'}</button>
        </div>
        <div class="ch-rp-podium">${podiumHtml}</div>
        <div class="ch-rp-lanes">${laneRows}</div>
        <div class="ch-rp-foot"><span><i class="pl"></i>you</span><span><i class="rv"></i>rivals</span><span class="ch-rp-note">animated by finish order — flight recorder, not a physics sim</span></div>
      </div>`;
    const o = I.modal({ title: 'RACE REPLAY', sub: 'flight recorder', wide: true, body });
    const wrap = o.querySelector('.ch-rp');
    const playBtn = o.querySelector('[data-rp-play]');
    const run = () => {
      if (!wrap) return;
      wrap.classList.remove('go');
      // force reflow so re-adding .go restarts the CSS transitions
      void wrap.offsetWidth;
      if (prefersReducedMotion()) { wrap.classList.add('go', 'done'); return; }
      wrap.classList.remove('done');
      wrap.classList.add('go');
      // reveal the podium once the runners have settled
      window.setTimeout(() => { if (wrap.isConnected) wrap.classList.add('done'); }, 1500);
    };
    if (playBtn) playBtn.addEventListener('click', run);
    // auto-start (reduced-motion immediately freezes on the podium)
    run();
  }
  // wire ▶ replay buttons in a freshly-rendered report
  function wireReplays(host, races) {
    host.querySelectorAll('[data-replay]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.dataset.replay);
        const r = races[idx];
        if (r) { r._trainee = (careers[activeIdx] && (careers[activeIdx].trainee || '').toUpperCase()) || 'YOU'; openReplayModal(r); }
      });
    });
  }

  // ---- 4) HEAD-TO-HEAD COMPARE ----------------------------------------------
  let compareMode = false;     // toggled by the VS button in the section header
  let rivalIdx = null;         // the second career picked from the list

  // pull the 5 compare metrics from a career
  function vsMetrics(c) {
    const st = c.stats || {};
    const total = (st.speed || 0) + (st.stamina || 0) + (st.power || 0) + (st.guts || 0) + (st.wit || 0);
    const races = c.races || (c.race_results ? c.race_results.length : 0);
    const wins = c.wins || 0;
    const sparks = (c.sparks && c.sparks.length) || 0;
    const skills = c.skills_grouped
      ? Object.values(c.skills_grouped).reduce((s, a) => s + ((a && a.length) || 0), 0)
      : 0;
    return {
      fans: c.fans_final || 0,
      skills,
      sparks,
      winrate: races ? (wins / races) : 0,
      total,
      _raw: { races, wins },
    };
  }
  const VS_AXES = [
    ['FANS', 'fans'], ['SKILLS', 'skills'], ['SPARKS', 'sparks'],
    ['WIN %', 'winrate'], ['STATS', 'total'],
  ];

  // inline radar (no app.js dependency)
  function radarSvg(vals, side, lose) {
    const W = 220, cx = W / 2, cy = W / 2, R = 78, n = VS_AXES.length;
    const ang = (i) => (-Math.PI / 2) + (i / n) * Math.PI * 2;
    let grid = '';
    [0.25, 0.5, 0.75, 1].forEach((g) => {
      const pts = VS_AXES.map((_, i) => `${(cx + Math.cos(ang(i)) * R * g).toFixed(1)},${(cy + Math.sin(ang(i)) * R * g).toFixed(1)}`).join(' ');
      grid += `<polygon class="rd-grid" points="${pts}"/>`;
    });
    let axes = '', labels = '';
    VS_AXES.forEach(([lbl], i) => {
      const x = cx + Math.cos(ang(i)) * R, y = cy + Math.sin(ang(i)) * R;
      axes += `<line class="rd-axis" x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/>`;
      const lx = cx + Math.cos(ang(i)) * (R + 14), ly = cy + Math.sin(ang(i)) * (R + 14);
      const anchor = Math.abs(Math.cos(ang(i))) < 0.3 ? 'middle' : (Math.cos(ang(i)) > 0 ? 'start' : 'end');
      labels += `<text class="rd-lbl" x="${lx.toFixed(1)}" y="${(ly + 3).toFixed(1)}" text-anchor="${anchor}" fill="${lose ? 'var(--label)' : (side === 'a' ? 'var(--amber)' : 'var(--cyan)')}">${esc(lbl)}</text>`;
    });
    const poly = VS_AXES.map(([, key], i) => {
      const v = Math.max(0.04, Math.min(1, vals[key]));
      return `${(cx + Math.cos(ang(i)) * R * v).toFixed(1)},${(cy + Math.sin(ang(i)) * R * v).toFixed(1)}`;
    }).join(' ');
    return `<svg viewBox="0 0 ${W} ${W}" role="img">${grid}${axes}<polygon class="rd-poly" points="${poly}"/>${labels}</svg>`;
  }

  // normalise both careers' metrics to 0..1 against the pairwise max for the radar
  function normPair(a, b) {
    const out = [{}, {}];
    VS_AXES.forEach(([, key]) => {
      if (key === 'winrate') { out[0][key] = a[key]; out[1][key] = b[key]; return; }
      const mx = Math.max(1, a[key], b[key]);
      out[0][key] = a[key] / mx; out[1][key] = b[key] / mx;
    });
    return out;
  }

  function openCompareModal(a, b) {
    const ma = vsMetrics(a), mb = vsMetrics(b);
    const [na, nb] = normPair(ma, mb);
    // verdict tally: who wins each of the 5 axes
    let aWins = 0, bWins = 0;
    const barRows = VS_AXES.map(([lbl, key]) => {
      const va = ma[key], vb = mb[key];
      const mx = Math.max(1e-9, va, vb);
      const fa = (va / mx) * 100, fb = (vb / mx) * 100;
      const aBetter = va > vb, bBetter = vb > va;
      if (aBetter) aWins++; else if (bBetter) bWins++;
      const fmtV = (v) => key === 'winrate' ? Math.round(v * 100) + '%' : (key === 'fans' ? fmtCompact(v) : fmtNum(Math.round(v)));
      return `
        <div class="ch-vs-bar">
          <div class="ch-vs-bar-side a${aBetter ? '' : ' lose'}"><span class="fill" style="width:${fa.toFixed(0)}%"></span><span class="ch-vs-bar-v">${esc(fmtV(va))}</span></div>
          <div class="ch-vs-bar-k">${esc(lbl)}</div>
          <div class="ch-vs-bar-side b${bBetter ? '' : ' lose'}"><span class="fill" style="width:${fb.toFixed(0)}%"></span><span class="ch-vs-bar-v">${esc(fmtV(vb))}</span></div>
        </div>`;
    }).join('');
    const aWon = aWins > bWins, bWon = bWins > aWins;
    const crown = aWon ? '◀ ' + esc((a.trainee || 'RUN A').toUpperCase()) + ' TAKES IT'
      : bWon ? esc((b.trainee || 'RUN B').toUpperCase()) + ' TAKES IT ▶'
      : 'DEAD HEAT';
    const body = `
      <div class="ch-vs">
        <div class="ch-vs-hd">
          <div class="ch-vs-name a ${aWon ? 'win' : 'lose'}">${esc(a.trainee || 'RUN A')}<div class="ch-vs-sub">RUN #${esc(String(a.index))} · ${esc(a.career_rank || a.grade || '—')}</div></div>
          <div class="ch-vs-vs">VS</div>
          <div class="ch-vs-name ${bWon ? 'win' : 'lose'}">${esc(b.trainee || 'RUN B')}<div class="ch-vs-sub">RUN #${esc(String(b.index))} · ${esc(b.career_rank || b.grade || '—')}</div></div>
        </div>
        <div class="ch-vs-radars">
          <div class="ch-vs-radar a ${aWon ? '' : 'lose'}">${radarSvg(na, 'a', !aWon && bWon)}</div>
          <div class="ch-vs-radar b ${bWon ? '' : 'lose'}">${radarSvg(nb, 'b', !bWon && aWon)}</div>
        </div>
        <div class="ch-vs-bars">${barRows}</div>
        <div class="ch-vs-verdict">
          <div style="text-align:center"><div class="ch-vs-tally ${aWon ? 'win' : aWins === bWins ? 'tie' : ''}">${aWins}</div><div class="ch-vs-tally-k">${esc(a.trainee || 'A')}</div></div>
          <div class="ch-vs-crown ${aWon ? 'c-amber' : bWon ? 'c-cyan' : 'c-mut'}">${crown}</div>
          <div style="text-align:center"><div class="ch-vs-tally b ${bWon ? 'win' : aWins === bWins ? 'tie' : ''}">${bWins}</div><div class="ch-vs-tally-k">${esc(b.trainee || 'B')}</div></div>
        </div>
      </div>`;
    I.modal({ title: 'HEAD TO HEAD', sub: 'compare runs', wide: true, body });
  }

  function compareBtnHtml() {
    return `<button type="button" class="ch-vsbtn${compareMode ? ' is-on' : ''}" id="ch-vs-btn">${compareMode ? '✕ EXIT COMPARE' : '⇄ COMPARE THIS RUN'}</button>`;
  }

  function renderReport() {
    const c = careers[activeIdx];
    const host = $('ch-report');
    if (!c) { host.innerHTML = ''; return; }
    const p = profileFor(c);
    const st = c.stats || {};
    const FS = [['SPD', st.speed], ['STA', st.stamina], ['POW', st.power], ['GUT', st.guts], ['WIT', st.wit]];
    const aptOrder = ['TRACK', 'DISTANCE', 'STYLE'];

    // Prefer real per-career data; fall back to the mock for older/partial rows.
    const aptitudes = aptFromBackend(c) || p.aptitudes;
    const sparkRows = sparkTuples(c, p);
    const skillGroups = c.skills_grouped && typeof c.skills_grouped === 'object' ? c.skills_grouped : null;
    const realRaces = (c.race_results && c.race_results.length) ? c.race_results.map(adaptRace) : null;
    const races = realRaces || p.races;
    const ratingNum = Number(c.rating) || Number(p.rating) || 0;
    const careerGrade = (c.career_grade != null && c.career_grade !== '') ? c.career_grade : p.career_grade;
    const majorWins = c.major_wins
      ? (Array.isArray(c.major_wins) ? c.major_wins.join(', ') : String(c.major_wins))
      : (p.major_wins || []).join(', ');
    const raceCount = c.races || races.length;
    const winRate = raceCount ? Math.round(((c.wins || 0) / raceCount) * 100) : p.win_rate;
    const raceFans = realRaces ? realRaces.reduce((s, r) => s + (r.fans || 0), 0) : p.race_fans;

    host.className = 'col bordered prof';
    host.innerHTML = `
      <div class="prof-scroll">
        <!-- header -->
        <div class="prof-hd">
          <div class="prof-av">${(c.card_id || c.portrait_url) ? `<img src="${c.card_id ? '/api/card-art/' + esc(String(c.card_id)) + '.png?v=2' : esc(c.portrait_url)}" alt="${esc(c.trainee || 'trainee')}" onerror="this.remove()">` : '<span>TRAINEE</span>'}</div>
          <div class="prof-id">
            <div class="prof-name">${esc(c.trainee)}</div>
            <div class="prof-sub">${esc(c.scenario || p.scenario_label)}${c.finished_at ? ' · ' + esc(fmtWhen(c.finished_at)) : (p.date && p.date !== '—' ? ' · ' + esc(p.date) : '')}</div>
            ${c.run_id ? `<a class="loglink" href="logview.html?run_id=${encodeURIComponent(c.run_id)}" target="_blank" rel="noopener" title="Open the full turn-by-turn career log in the viewer">📋 VIEW FULL LOG</a>` : ''}
          </div>
          <div class="prof-rate">
            <div class="prof-circle">${esc(String(c.career_rank || careerGrade || '—'))}</div>
            <div class="prof-rate-v">${fmtNum(ratingNum)}</div>
            <div class="prof-rate-k">RATING</div>
          </div>
        </div>

        <!-- stat cards -->
        <div class="scards">
          <div class="scard"><div class="scard-v">${fmtNum(c.fans_final)}</div><div class="scard-k">FANS</div></div>
          <div class="scard"><div class="scard-v">${c.races || 0}</div><div class="scard-k">RACES</div></div>
          <div class="scard"><div class="scard-v">${c.wins || 0}</div><div class="scard-k">WINS</div></div>
          <div class="scard"><div class="scard-v amber">${esc(String(c.career_rank || careerGrade || '—'))}</div><div class="scard-k">RATING RANK</div></div>
          ${majorWins ? `<div class="scard wide"><div class="scard-v">${esc(majorWins)}</div><div class="scard-k">MAJOR WINS</div></div>` : ''}
        </div>

        <!-- 78-turn career heatmap (additive) -->
        ${(c.race_results && c.race_results.length) ? heatmapHtml(c) : ''}

        <!-- race trace ribbon (additive) -->
        ${(c.race_results && c.race_results.length) ? traceHtml(c) : ''}

        <!-- final stats + aptitudes -->
        <div class="prof-sec">
          <div class="prof-split">
            <div>
              ${finalStatsHtml(st, FS)}
            </div>
            <div>
              <div class="prof-sec-t">APTITUDES</div>
              ${aptOrder.map((k) => aptitudes[k] ? `
                <div class="aptrow"><div class="aptrow-k">${k}</div><div class="aptset">${aptSetHtml(aptitudes[k])}</div></div>` : '').join('')}
            </div>
          </div>
        </div>

        <!-- sparks -->
        ${sparkRows && sparkRows.length ? `
        <div class="prof-sec">
          <div class="prof-sec-t">SPARKS</div>
          <div class="sparks">
            ${sparkRows.map(([name, stars, pts]) => `
              <span class="sparkchip">${esc(name)} <span class="stars"><span class="stars-on">${'★'.repeat(Math.max(0, Math.min(3, stars)))}</span><span class="stars-off">${'☆'.repeat(Math.max(0, 3 - stars))}</span></span> <span class="pts">+${pts} pts</span></span>`).join('')}
          </div>
        </div>` : ''}

        <!-- skills gained -->
        ${skillGroups && Object.keys(skillGroups).length ? `
        <div class="prof-sec">
          <div class="prof-sec-t">SKILLS GAINED</div>
          ${Object.entries(skillGroups).map(([label, arr]) => (arr && arr.length) ? `
            <div class="aptrow"><div class="aptrow-k">${esc(String(label).toUpperCase())}</div><div class="sparks">${arr.map((sk) => `<span class="skillchip">${esc(sk && (sk.name || sk.skill_name) || sk)}</span>`).join('')}</div></div>` : '').join('')}
        </div>` : ''}

        <!-- head-to-head compare affordance (additive) -->
        <div class="ch-sec">
          <div class="ch-sec-hd">
            <span class="ch-sec-t">HEAD TO HEAD</span>
            <span class="ch-sec-spacer"></span>
            ${compareBtnHtml()}
          </div>
          <div class="ch-sec-note">${compareMode ? '<b style="color:var(--cyan)">Now click a second run in the list on the left</b> — the two will open side-by-side. (Or use the banner above the list to cancel.)' : 'Compare this run against another completed career — fans, skills, sparks, win-rate and total stats. Click below, then pick a rival from the left.'}</div>
        </div>

        <!-- race history -->
        <div class="rh-head">
          <span class="t">RACE HISTORY</span>
          <span class="rh-stat"><b>${raceCount}</b> races</span>
          <span class="rh-stat"><b>${c.wins || 0}</b> wins</span>
          <span class="rh-stat"><b>${winRate}%</b> win rate</span>
          <span class="rh-stat"><b>${fmtNum(raceFans)}</b> race fans</span>
        </div>
        ${calibrationHtml(races)}
        <div class="rh-list">
          ${races.map(raceRowHtml).join('')}
        </div>
      </div>`;

    // ---- post-render wiring for the upgrades --------------------------------
    wireHolo(host, c.career_rank || careerGrade);   // holo foil + tilt on the avatar
    wireHeatTips(host);                              // heatmap cell tooltips
    wireStatToggle(host);                            // FINAL STATS bars/radar tabs
    wireReplays(host, races);                        // ▶ race-replay buttons
    const vsBtn = host.querySelector('#ch-vs-btn');
    if (vsBtn) vsBtn.addEventListener('click', () => {
      compareMode = !compareMode;
      if (!compareMode) rivalIdx = null;
      renderList(); renderReport();                 // re-render to reflect pick mode (renderList syncs the persistent bar)
    });
  }

  async function boot() {
    ensureCoolStyles();   // lazy-inject our own stylesheet (once)
    tagCoolRoot();        // expose the local place-tone aliases on <body>
    I.mountChrome();
    const data = await api('/api/career/history');
    careers = (data && data.careers) || [];
    careers.forEach((c) => {
      if (c.grade == null) c.grade = c.career_rank;
      if (c.fans_final == null) c.fans_final = c.fans_gained || 0;
    });
    activeIdx = careers.length ? 0 : null;
    renderList(); renderReport();

    $('ch-filter').addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      [...$('ch-list').children].forEach((row, i) => {
        const c = careers[i];
        row.style.display = (!q || (c.trainee || '').toLowerCase().includes(q) || String(c.index).includes(q)) ? '' : 'none';
      });
    });
  }
  boot();
})();
