#!/usr/bin/env node
'use strict';

/*
  Local Trackblazer solver bridge for Eden Bot.

  This is intentionally dependency-free so it can run anywhere Node is installed.
  It reads a JSON payload from stdin and returns a bot-ready schedule on stdout.

  Payload fields:
    races: Trackblazer races.json array
    programs: [{program_id, turn, name}]
    aptitudes: {Sprint,Mile,Medium,Long,Turf,Dirt}
    options: {fan_bonus, max_races_in_row, include_op, min_aptitude_floor, weights, training_blocks, manual_locks}
*/

const fs = require('fs');

const APT_VALUE = { G: 1, F: 2, E: 3, D: 4, C: 5, B: 6, A: 7, S: 8 };
const DIST_KEYS = { Sprint: 'proper_distance_short', Mile: 'proper_distance_mile', Medium: 'proper_distance_middle', Long: 'proper_distance_long' };
const SURF_KEYS = { Turf: 'proper_ground_turf', Dirt: 'proper_ground_dirt' };
const GRADE_REWARD = {
  G1: { stats: 10, sp: 35, fans: 10000, grade: 5 },
  G2: { stats: 8, sp: 25, fans: 6000, grade: 4 },
  G3: { stats: 8, sp: 25, fans: 4500, grade: 3 },
  OP: { stats: 5, sp: 15, fans: 2400, grade: 2 },
  'PRE-OP': { stats: 5, sp: 10, fans: 1300, grade: 1 },
  PREOP: { stats: 5, sp: 10, fans: 1300, grade: 1 },
  'Pre-OP': { stats: 5, sp: 10, fans: 1300, grade: 1 },
};

function slug(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function aptValue(value, fallback = 7) {
  if (Number.isFinite(value)) return value;
  return APT_VALUE[String(value || 'A').toUpperCase()] || fallback;
}

function raceOk(race, aptitudes, floor) {
  const distance = race.distance;
  const surface = race.surface;
  const dVal = aptValue(aptitudes[distance] || aptitudes[DIST_KEYS[distance]]);
  const sVal = aptValue(aptitudes[surface] || aptitudes[SURF_KEYS[surface]]);
  return dVal >= floor && sVal >= floor;
}

function scoreRace(row, weights) {
  const reward = GRADE_REWARD[row.grade] || GRADE_REWARD[String(row.grade || '').toUpperCase()] || { stats: 0, sp: 0, grade: 0 };
  const fanW = Number(weights.fans ?? 1.0);
  const statW = Number(weights.stats ?? 150.0);
  const spW = Number(weights.skill_points ?? 45.0);
  const gW = Number(weights.grade ?? 800.0);
  return (row.est_fans * fanW) + (reward.stats * statW) + (reward.sp * spW) + (reward.grade * gW);
}

function buildRows(payload) {
  const races = Array.isArray(payload.races) ? payload.races : [];
  const programs = Array.isArray(payload.programs) ? payload.programs : [];
  const aptitudes = payload.aptitudes || {};
  const opt = payload.options || {};
  const includeOp = !!opt.include_op;
  const floor = Number(opt.min_aptitude_floor ?? 6);
  const fanBonus = Number(opt.fan_bonus || 0);
  const programByName = new Map();
  for (const program of programs) {
    const nameKey = slug(program.name);
    if (!nameKey) continue;
    if (!programByName.has(nameKey)) programByName.set(nameKey, []);
    programByName.get(nameKey).push(program);
  }

  const rows = [];
  for (const race of races) {
    const grade = String(race.grade || '').toUpperCase();
    if (!includeOp && ['OP', 'PRE-OP', 'PREOP'].includes(grade)) continue;
    if (!raceOk(race, aptitudes, floor)) continue;
    const matches = programByName.get(slug(race.name)) || [];
    for (const match of matches) {
      const fans = Number(race.fans || 0);
      const turn = Number(match.turn || 0);
      const programId = Number(match.program_id || 0);
      if (!turn || !programId) continue;
      rows.push({
        program_id: programId,
        turn,
        name: race.name || match.name || '',
        grade,
        distance: race.distance || null,
        surface: race.surface || null,
        fans,
        est_fans: Math.round(fans * (1 + fanBonus / 100.0)),
      });
    }
  }
  return rows;
}

function solve(payload) {
  const opt = payload.options || {};
  const weights = opt.weights || {};
  const maxStreak = Math.max(1, Number(opt.max_races_in_row ?? 2));
  const trainingBlocks = new Set((opt.training_blocks || []).map(Number));
  const manualLocks = opt.manual_locks || {}; // {turn: program_id|'training'|null}
  const rows = buildRows(payload);
  for (const row of rows) row.score = scoreRace(row, weights);

  const byTurn = new Map();
  for (const row of rows) {
    if (!byTurn.has(row.turn)) byTurn.set(row.turn, []);
    byTurn.get(row.turn).push(row);
  }

  const turns = [...byTurn.keys(), ...Object.keys(manualLocks).map(Number), ...trainingBlocks].filter(Boolean);
  const minTurn = turns.length ? Math.min(...turns) : 1;
  const maxTurn = turns.length ? Math.max(...turns) : 72;

  // DP state: key = streak, value = {score, selected}
  let states = new Map([[0, { score: 0, selected: [] }]]);
  for (let turn = minTurn; turn <= maxTurn; turn++) {
    const lock = manualLocks[String(turn)] ?? manualLocks[turn];
    const candidates = [];
    const forceTraining = trainingBlocks.has(turn) || lock === null || lock === 'training' || lock === 'none' || lock === 'no_race';
    if (!forceTraining) {
      const turnRows = (byTurn.get(turn) || []).sort((a, b) => b.score - a.score);
      if (lock) {
        const wanted = Number(lock);
        const lockedRace = turnRows.find(r => r.program_id === wanted);
        if (lockedRace) candidates.push(lockedRace);
      } else {
        candidates.push(...turnRows.slice(0, Number(opt.max_candidates_per_turn ?? 8)));
      }
    }
    // null means train/rest/no-race. Always valid unless the user locked a race that exists.
    if (!lock || forceTraining) candidates.push(null);

    const next = new Map();
    for (const [streakRaw, state] of states.entries()) {
      const streak = Number(streakRaw);
      for (const cand of candidates) {
        const nextStreak = cand ? streak + 1 : 0;
        if (cand && nextStreak > maxStreak) continue;
        const nextScore = state.score + (cand ? cand.score : 0);
        const key = nextStreak;
        const old = next.get(key);
        if (!old || nextScore > old.score) {
          next.set(key, { score: nextScore, selected: cand ? state.selected.concat([cand]) : state.selected.slice() });
        }
      }
    }
    if (next.size === 0) {
      return { success: false, solver: 'node-dp', detail: `No feasible schedule at turn ${turn}. Check forced races/max streak.` };
    }
    states = next;
  }

  let best = null;
  for (const state of states.values()) {
    if (!best || state.score > best.score) best = state;
  }
  const schedule = (best ? best.selected : []).map(r => {
    const out = { ...r };
    delete out.score;
    return out;
  });
  return {
    success: true,
    solver: 'node-dp',
    generated_at: Math.floor(Date.now() / 1000),
    race_count: schedule.length,
    estimated_fans: schedule.reduce((sum, r) => sum + Number(r.est_fans || 0), 0),
    objective_score: best ? Math.round(best.score) : 0,
    extra_race_list: schedule.map(r => r.program_id),
    schedule,
  };
}

function main() {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { raw += chunk; });
  process.stdin.on('end', () => {
    try {
      const payload = JSON.parse(raw || '{}');
      process.stdout.write(JSON.stringify(solve(payload), null, 2));
    } catch (err) {
      process.stdout.write(JSON.stringify({ success: false, solver: 'node-dp', detail: err.message }, null, 2));
      process.exitCode = 1;
    }
  });
}

main();
