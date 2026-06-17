# SweepyModv5.44 Event Outcome Knowledge Base

SweepyModv5.44 adds a safe Event Outcome Knowledge Base built around static/imported event outcome data. It does not include Frida, live traffic interception, packet capture, process hooks, memory reads, or memory writes.

## What it does

- Imports a static `outcomes.json` style map.
- Normalizes event names, choice indices, and reward deltas.
- Scores event choices using known stat, energy, motivation, skill-point, and skill-hint outcomes.
- Writes AI-ready event outcome rows to `uma_runtime/ai/event_outcome_rows.jsonl`.
- Shows Event Outcome KB coverage inside AI Learning.
- Adds known-outcome context to Local LLM post-run analysis and shadow review prompts.

## Bundled source

The build includes `data/dumper_outcomes_import.json`, which is a static outcomes map. Clicking **IMPORT BUNDLED OUTCOMES** merges it into `data/event_outcomes.json` and appends AI dataset rows.

## Runtime artifacts

- `data/event_outcomes.json`
- `data/dumper_outcomes_import.json`
- `uma_runtime/ai/event_outcome_rows.jsonl`
- `uma_runtime/ai/event_outcome_import_report.json`

## Dashboard

Open **AI Learning** and use the **Event Outcome Knowledge Base** card.

- **IMPORT BUNDLED OUTCOMES** merges the bundled static outcomes.
- **REFRESH EVENT KB** reloads the current coverage summary.

The card shows known events, known choices, imported static events, and unknown seen events.

## Local LLM interaction

The Local LLM Advisor receives a compact `event_outcome_knowledge` object in analysis prompts. This helps the model explain event-choice decisions using known static outcomes instead of guessing.

## Safety boundary

This feature only uses static/imported files. It does not perform live interception, memory dumping, process scanning, packet capture, or hook installation.
