# Smart Race Solver Settings

## Purpose

Smart Race Solver Settings moves solver-specific options out of the compact Trackblazer card and into a dedicated modal. The modal lets users tune aptitude filtering, OP/Pre-OP inclusion, summer racing, epithet targeting, scoring weights, fan bonus, and max race streak without crowding the setup dashboard.

## UI entry point

The Trackblazer card now shows a **SMART RACE SOLVER SETTINGS** button in the solver controls area. It opens a modal that uses the same dark card/window styling as Training Settings, Racing Settings, and Scenario Overrides.

## Functional settings

The modal includes these functional controls:

- **Active Mode**: displays whether the compact Trackblazer card is currently in Smart Race Solver or Manual Selection mode. Mode switching happens only on the compact card to avoid duplicate controls.
- **Character Preset**: shows and can change the active trainee selected in Setup.
- **Manual solver aptitudes**: lets the user override Sprint, Mile, Medium, Long, Turf, and Dirt aptitude grades used by the solver. Overrides are scoped per trainee. The modal displays Base, Manual Start, Estimated Parent Sparks, and Solver Final.
- **Aptitude Threshold**: sets the minimum distance and surface aptitude required for race eligibility.
- **Include OP / Pre-OP races**: lets the solver consider lower-grade races.
- **Allow racing during Summer**: when disabled, Classic/Senior summer-camp races are blocked by the solver. When enabled, those races may be scheduled but can still receive the configured summer penalty.
- **Target Epithets**: gives matching races an epithet value bonus.
- **Forced Epithets**: hard-constrains the solver so every selected forced epithet must have at least one matching scheduled race under the native matcher. If the current filters make that impossible, planning reports infeasible.
- **Optimization Mode**: switches between Stat Epithets and Fans + Epithets scoring presets.
- **Scoring Weights**: tunes race value, epithet value, fan weight, hint reward value, consecutive-race penalty, summer penalty, race bonus, race cost, fan bonus, and max streak.
- **Schedule Preview**: runs the solver with the current modal settings and shows the latest route preview.

## Persistence

Settings are saved on the active preset using these keys:

```json
{
  "trackblazer_solver_settings": {},
  "trackblazer_manual_aptitudes": {},
  "trackblazer_manual_aptitudes_by_trainee": {},
  "trackblazer_weights": {},
  "trackblazer_target_epithets": [],
  "trackblazer_forced_epithets": []
}
```

`career_bot/presets.py` preserves these fields during preset save/load.

## Solver integration

`public/app.js` builds the `/api/trackblazer/plan` payload from the active modal settings. The backend accepts `target_epithets` and `forced_epithets`, then `career_bot/trackblazer.py` annotates candidate races using a best-effort native matcher against epithet condition text.

The solver now scores matching races with:

- `epithetValue` for target epithet hits
- `forcedEpithetValue` for forced epithet hits
- `hintRewardWeight` as a small extra reward on matching G1 hint routes

Forced epithets are additionally enforced as hard native-matcher constraints. The matcher is not a formal proof that an epithet is complete, because the upstream cache supplies condition text rather than executable matcher bytecode. Race-name hits are exact text matches, while broad condition phrases such as Dirt, Mile, Sprint, G1, G2, and G3 mark matching race rows.

## Duplicate cleanup

The compact Trackblazer card no longer owns Include OP / Pre-OP, Fan Bonus %, or Max Streak inputs. Those settings now live in the Smart Race Solver Settings modal as the single source of truth. Racing Settings did not contain exact duplicates, so no Racing Settings controls were removed.

## Verification

1. Open Setup and confirm **SMART RACE SOLVER SETTINGS** appears in the Trackblazer card.
2. Change an aptitude or threshold, then click **SOLVE PREVIEW** and confirm the route changes or the plan is marked stale.
3. Toggle Include OP / Pre-OP and confirm OP/Pre-OP races appear only when enabled.
4. Select a target or forced epithet and confirm matching race rows receive solver preference.
5. Save/refresh and confirm the preset keeps all solver setting fields.
