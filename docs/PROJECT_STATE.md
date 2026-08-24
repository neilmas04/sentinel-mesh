# Project state

## Current milestone

**M01 complete — deterministic synthetic payment world.**

## Completed

- Versioned, seeded synthetic-world generator.
- Persistent merchants, accounts, devices, and synthetic network groups.
- Temporal train, validation, and held-out test cohorts.
- Separate model-safe transaction files and hidden ground-truth manifests.
- Nine required legitimate and suspicious scenario families.
- Static leakage and synthetic-artifact checks.
- Standard-library test suite for determinism and data-contract safety.

## Verified M01 artifact

- **Dataset version / seed:** `m01-world-v1` / `20260824`.
- **Scale:** 46,296 transactions; 2,340 abuse events; 45 merchants; 2,700
  accounts; 2,222 devices; 1,106 synthetic network groups.
- **Verification:** 3/3 M01 tests pass. Re-running the default generator
  produced an identical SHA-256 hash for every generated artifact. All 11
  current leakage and artifact checks pass.

## Deliberately deferred

- System A/B/C training and threshold selection.
- Server-side scoring, cases, API contract, and frontend integration.
- Agent redesign, Gemini grounding validation, audit logging, and circuit breaker.

## Current data contract

Model-facing transaction files contain only: `transaction_id`, `timestamp`,
`merchant_id`, `account_id`, `device_id`, `network_group_id`, `amount`,
`payment_category`, and `status`. Labels and scenarios are in
`ground_truth/` and must not enter feature frames.

## Known limitations

- All data is synthetic and cannot support production-performance claims.
- M01 validates simulation-data leakage only; model-feature point-in-time
  tests begin in M02.
- The prototype's existing virtual environment references a missing base
  Python installation. Use a newly created environment from `requirements.txt`.

## Next task

**M02 — implement a leakage-safe System A merchant-local baseline, validation
threshold selection, persisted artifacts, and held-out evaluation.**
