# Experiments

## M01 — Synthetic Coordinated-Abuse World
- **Purpose:** Establish a deterministic, leakage-audited dataset foundation for evaluating coordinated abuse detection.
- **Synthetic Nature:** The dataset is entirely synthetic, simulating organic and fraudulent transactions across a merchant network.
- **Role:** Serves as a controlled environment to isolate and measure the impact of specific feature families (network, temporal) without the noise and privacy constraints of real-world data.
- **Separation:** Strictly separated into temporal cohorts: Train, Validation, and Held-out Test. Campaigns never cross cohorts, and entities (accounts, devices, networks) are cohort-disjoint.

## M02 — Baseline
- **Role:** Establishes a scientifically defensible local baseline (System A) using only merchant-local decision-time features.
- **Results:** Demonstrated that a local-only model can detect some abuse but suffers from slower Time-to-Detection (TTD) and lower recall compared to network-aware models. (See `artifacts/experiments/m02_baseline/metadata.json`).

## M03 — Network Detection
- **Role:** Evaluates the incremental value of cross-merchant network intelligence (System B) over the local baseline.
- **Results:** Network features (especially Device and Account cross-merchant tracking) dramatically improved F1 and reduced Expected Cost. Confirmed the hypothesis that cross-merchant graph signals improve detection. (See `artifacts/experiments/m03_system_b/metadata.json`).

## M04 — Temporal / Robustness
- **Role:** Evaluates the incremental value of temporal and emerging-risk features (System C) over the network baseline.
- **Results:** Temporal signals (synchronization and growth rates) cut detection times significantly and reduced expected operational cost. (See `artifacts/experiments/m04_system_c/metadata.json`).

## M05 / Candidate D
- **Model Role:** Candidate D is the core Sentinel detector, selected for its optimal balance of speed, coverage, and robustness.
- **Feature Families:** Combines network synchronization and growth features with the baseline local and network features.
- **Thresholding:** Uses strict cost-aware thresholding selected on the validation set.
- **Relationship to Calibration:** Candidate D's raw outputs were later subjected to probability calibration analysis (M13). Note: Calibrated probabilities are **not** used by the PolicyEngine; it relies on the raw scores and deterministic rules.
- **Relationship to Robustness:** Candidate D was selected during the M04-R robustness evaluation because it maintained perfect campaign coverage even under adversarial low-and-slow attacks, unlike more brittle models.

## M11 — Merchant Spike Timeline
- **Bucket-Level Baseline:** Maintains historical transaction volume baselines for merchants.
- **Live Bucket:** Compares live transaction volume against the historical baseline.
- **Timeline Visualization:** Provides a visual representation of the spike timeline in the frontend dashboard.
- **Insufficient-History Behavior:** Gracefully handles merchants with insufficient history by suppressing spike alerts until a baseline is established.
- **Integration:** HIGH or CRITICAL spike events are integrated into the deterministic case aggregation pipeline as case signals.

## M12 — External Transaction-Level Benchmark
- **Dataset:** Kaggle ULB Credit Card Fraud Detection.
- **Rows:** 284,807
- **Fraud Count:** 492
- **Temporal Split:**
  - Train: 182,276
  - Validation: 45,569
  - Test: 56,962
- **Threshold Selection:** Validation-only threshold selection (Selected threshold = 0.7511).
- **Results (Test Set):**
  - PR-AUC: 0.7958
  - Precision: 0.8250
  - Recall: 0.8148
  - F1: 0.8199
  - False Positives: 14
  - False Negatives: 15
  - Normalized Cost: $8,900 (under the explicitly stated Sentinel Mesh benchmark assumption)
  - Benchmark-specific cost: $3,736.05 (under the explicitly stated transaction-amount assumption)
- **Important Note:** This evaluates a transaction-level benchmark model and does **NOT** validate Candidate D's network/temporal coordinated-abuse capability. The features and data differ significantly from M01.
- **Reference:** `artifacts/experiments/m12_external_benchmark/benchmark_report.md`

## M13 — Probability Calibration
Documenting the completed leakage-safe calibration protocol.
- **Methods:** Isotonic Regression, Sigmoid / Platt Scaling.
- **Protocol:**
  - 5-fold CV on validation split only for method selection.
  - Selected method fitted on full validation set.
  - Frozen before test evaluation.
  - Test labels never used for fitting or method selection.

**Candidate D:**
- CV Brier Isotonic = 0.005604
- CV Brier Sigmoid = 0.005621
- Selected = Isotonic
- Test raw Brier = 0.010454
- Test calibrated Brier = 0.011194 (Note: Calibrated TEST Brier is slightly worse than raw Brier)
- Test raw ECE = 0.022229
- Test calibrated ECE = 0.010040 (ECE improves)

**External Benchmark:**
- CV Brier Isotonic = 0.000397
- CV Brier Sigmoid = 0.000482
- Selected = Isotonic
- Test raw Brier = 0.009653
- Test calibrated Brier = 0.000430
- Test raw ECE = 0.080568
- Test calibrated ECE = 0.000202

**Important Note:** Calibration is an analytical experiment. It is **not** exposed to or used by the PolicyEngine, and it is not a proof of real-world probability validity.

## M14 — Adversarial Robustness
Documenting the full robustness methodology against synthetic perturbations.
- **Attack Families:** Timing jitter, low-and-slow, merchant hopping, device rotation, account rotation, fragmented bursts.
- **Pre-improvement findings:**
  - Clean F1 = 0.8837
  - Clean TTD = 3.63 min
  - Low-and-Slow 24x F1 = 0.4123
  - Low-and-Slow 24x TTD = 247.0 min
  - Largest TTD degradation = +243.4 min
  - Largest cost increase = +$50,800
- **Root Cause:** Short-term temporal/local velocity signals collapse under low-and-slow attacks, while longer-horizon network/growth signals remain informative. Eventual campaign detection remains high despite poor early transaction-level detection.
- **Early Warning:**
  - Version = `early_warning_v1`
  - Validation-selected OR rule: `network_device_accounts_24h > 5.0` OR `temporal_device_new_accounts_1h > 1.0`
  - Target validation FPR <= 0.5%
- **Post-improvement:**
  - 24x TTD: 247.0 min → 116.2 min (Improvement = 130.8 min)
  - 10x TTD: 67.6 min → 26.1 min (Improvement = 41.5 min)
  - Clean incremental FPs = approximately +14 to +15 depending on evaluation context.
  - No observed TTD/campaign-coverage regressions across the tested full grid.
- **Important Note:** The Early Warning detector is parallel to Candidate D, causal, and investigation-oriented. It is **not** an autonomous blocking mechanism. Robustness results come from synthetic perturbations and do not establish robustness to all real-world attacks.

## M15 — Alert Aggregation / Analyst Workflow
- **Deterministic Grouping:** Entity + temporal grouping of signals.
- **Grouping Window:** 24-hour rolling window.
- **Parent Case:** Signals are aggregated into a parent case.
- **Case Signals:** Individual alerts (Candidate D, Early Warning, Merchant Spike) are attached as `case_signals`.
- **Duplicate Protection:** Duplicate signals for the same entity within the window are merged.
- **Aggregation:** Integrates Early Warning, Candidate D, and Merchant Spike signals.
- **Analyst Workflow:** Supports analyst disposition and maintains an immutable audit log.
- **AI Failure:** Preserves context and degrades gracefully to deterministic rules if the AI fails.
- **Browser Verification:** Key case flows verified via browser E2E tests.

## RESULT INTERPRETATION
**How to Interpret the Evidence**
Clearly distinguish the following aspects of the evaluation:
1. **Simulated coordinated-abuse capability:** Evaluated in M01-M04 using synthetic data.
2. **Transaction-level external benchmark capability:** Evaluated in M12 using a real-world, but non-network, dataset.
3. **Probability calibration analysis:** An offline analytical experiment (M13).
4. **Synthetic adversarial robustness:** Evaluated in M14 using synthetic perturbations of the M01 dataset.
5. **Production-oriented case workflow:** The runtime aggregation and investigation pipeline (M15).
Do not combine these distinct evaluations into one aggregate accuracy claim.

## TRACEABILITY
- M02 Baseline Results: `artifacts/experiments/m02_baseline/metadata.json`
- M03 Network Results: `artifacts/experiments/m03_system_b/metadata.json`
- M04 Temporal Results: `artifacts/experiments/m04_system_c/metadata.json`
- M12 Benchmark Results: `artifacts/experiments/m12_external_benchmark/benchmark_report.md`
- M13 Calibration Results: `artifacts/experiments/m13_calibration/`
- M14 Robustness Results: `artifacts/experiments/m14_robustness/`
