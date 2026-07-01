---
slug: shop-optimizer-spec-v3
date: 2026-07-01
description: Apply 10-point feedback to SHOP_OPTIMIZER_SPEC.md — split deterministic optimizer naming, add record eligibility classes, shadow mode, policy decision record, canonical item IDs, fixture categories, rounding rules, and coding-agent hard rules.
---

## Task

Apply all 10 feedback items to SHOP_OPTIMIZER_SPEC.md.

## Changes Required

1. Split "deterministic optimizer" into `deterministic_shop_policy` (live decision) and `shop_learning_optimizer` (post-career learning). Update all references throughout the document.
2. Add `record_eligibility` field to the career record with values: `direct_learning`, `observational_learning`, `diagnostic_only`, `excluded_manual`, `invalid`.
3. Add explicit rule: only `direct_learning` records may update deterministic clean-career means.
4. Add `native_with_deterministic_shadow` as an optional frontend policy mode, with shadow decision fields in the turn-level shop log.
5. Add `policy_decision` structured object to the turn-level shop log.
6. Require canonical item IDs (`item_id`) alongside display names. Rename `canonical_item_names.json` → `canonical_items.json` in the repo structure. Add canonical item schema.
7. Split conformance fixtures into 7 purpose-specific subdirectories.
8. Add deterministic rounding rules (half-away-from-zero, with examples).
9. Add hard rule for coding agents: do not mutate native policy except for thin telemetry hooks.
10. Add "Record Eligibility Rules" section.

## Files

- `SHOP_OPTIMIZER_SPEC.md` — primary target
