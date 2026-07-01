---
slug: shop-optimizer-spec-v3
status: complete
date: 2026-07-01
---

## Applied

All 10 feedback items applied to SHOP_OPTIMIZER_SPEC.md.

1. **Terminology split** — "deterministic optimizer" disambiguated into `deterministic_shop_policy` (live decisions) and `shop_learning_optimizer` (post-career learning). Updated throughout: glossary, Two Layers → Three Components, architecture diagrams, adapter functions, interop manifest, LLM section, feedback loop diagram, Run Score section.

2. **Record eligibility field** — `record_eligibility` added to the career record with values `direct_learning`, `observational_learning`, `diagnostic_only`, `excluded_manual`, `invalid`. Full computation logic and a dedicated "Record Eligibility Rules" section added.

3. **Clean-career mean protection** — Explicit rule in Step 2 of the learning optimizer: only `record_eligibility = "direct_learning"` records may update clean-career means. `observational_learning` contributes to waste flag rates only.

4. **Shadow mode** — `native_with_deterministic_shadow` added as a supported policy mode in glossary, frontend toggle, policy router diagram, interop manifest, and implementation checklist. Shadow decision fields added to turn-level shop log.

5. **Policy decision record** — Structured `policy_decision` object added to turn-level shop log with `decision_type`, `item_id`, `reason_code`, `score`, `policy_mode`, `executed` fields.

6. **Canonical item IDs** — Item Reference tables updated to include canonical IDs (e.g. `vita_40`, `master_cleat_hammer`). `shop_items_offered` and all item fields in turn logs use IDs not display names. `canonical_item_names.json` renamed to `canonical_items.json` in repo structure. Adapter checklist item added.

7. **Fixture categories** — Conformance fixtures split into 7 purpose-specific subdirectories: `schema_fixtures`, `waste_flag_fixtures`, `scoring_fixtures`, `optimizer_adjustment_fixtures`, `guardrail_fixtures`, `knowledge_pack_import_fixtures`, `canonical_hash_fixtures`. Repo structure updated with representative filenames.

8. **Deterministic rounding rule** — Half-away-from-zero rule specified with examples. Language-specific hazards (Python banker's rounding, JS `Math.round`) called out explicitly. Rule placed immediately after the adjustment formula in Step 2.

9. **Native policy immutability rule** — Hard rule for coding agents added to Separation Mandate: native policy must not be refactored, rewritten, or tuned except for the minimal telemetry hook needed for instrumentation.

10. **Record Eligibility Rules section** — Full standalone section added before Recommended Repository Structure, covering: eligibility values table, computation algorithm, what each level can/cannot do, and the critical rule statement.
