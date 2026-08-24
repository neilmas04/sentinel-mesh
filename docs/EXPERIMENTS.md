# Experiments

## M01-DATA-001 — synthetic-world construction

- **Purpose:** establish a deterministic, leakage-audited dataset foundation.
- **Dataset:** `m01-world-v1`, seed `20260824`.
- **Model:** none; this is not a detection benchmark.
- **Result:** 46,296 events (2,340 abuse), 45 merchants, 2,700 accounts,
  2,222 devices, and 1,106 network groups. All 11 leakage/artifact checks
  passed; a full regeneration produced byte-identical artifacts.
- **Artifacts:** generation and leakage results are written with the dataset in
  `manifests/summary.json` and `manifests/leakage_report.json`.
- **Conclusion:** M01 creates data only. It makes no claim that network or
  temporal intelligence improves detection.
- **Next action:** implement and pre-register System A evaluation as M02.
