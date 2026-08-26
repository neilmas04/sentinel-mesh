# Project state

## Current milestone

**M08 complete — Deterministic Policy + Risk Economics + Decision Layer.**

## Completed Milestones
- [x] M01 - Synthetic World Generator
- [x] M02 - Baseline Model (System A)
- [x] M03 - Network Graph Features (System B)
- [x] M04 - Temporal Coordinated Behavior (System C)
- [x] M04-R - Robustness & Generalization Evaluation
- [x] M05 - Server-Side Risk Scoring + Case Creation
- [x] M06 - Evidence-Led Agentic Investigation
- [x] M07 - Live Generative AI Verification + Evidence Grounding
- [x] M08 - Deterministic Policy + Risk Economics + Decision Layer

## Current Status
- Sentinel now evaluates risk via Candidate D model, constructs structural cases, and initiates an investigation loop.
- A deterministic Policy Engine wraps the AI assessment, strictly enforcing cost-based boundaries and manual review fallbacks.
- The next step (M09) will involve building the UI dashboard for analysts to consume this backend payload.

## Verified M01 artifact

- **Dataset version / seed:** `m01-world-v1` / `20260824`.
- **Scale:** 46,296 transactions; 2,340 abuse events; 45 merchants; 2,700
  accounts; 2,222 devices; 1,106 synthetic network groups.
- **Verification:** 3/3 M01 tests pass. Re-running the default generator
  produced an identical SHA-256 hash for every generated artifact. All 11
  current leakage and artifact checks pass.

## Deliberately deferred

- Agent redesign, Gemini grounding validation, audit logging, and circuit breaker.
- Frontend redesign and integration.

## Current data contract

Model-facing transaction files contain only: `transaction_id`, `timestamp`,
`merchant_id`, `account_id`, `device_id`, `network_group_id`, `amount`,
`payment_category`, and `status`. Labels and scenarios are in
`ground_truth/` and must not enter feature frames.

## Known limitations

- All data is synthetic and cannot support production-performance claims.
- The prototype's existing virtual environment references a missing base
  Python installation. Use a newly created environment from `requirements.txt`.
- Highly strict cost-aware thresholds penalize highly sparse abuse campaigns resulting in slightly reduced overall coverage (0.88 - 0.75) for models reliant on growth-rate features.
- Candidate D remains susceptible to low-and-slow execution (F1 drops to 0.79 under a 5x temporal expansion), though it preserves 100% campaign coverage.

## Next task

**M06 — Agentic GenAI Investigation / Automated Dossier Generation.**
