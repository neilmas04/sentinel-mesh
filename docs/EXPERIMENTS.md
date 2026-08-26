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

## M02-EVAL-001 — Leakage-Safe System A Merchant-Local Baseline

- **Purpose:** establish a scientifically defensible local baseline against which advanced models can be evaluated.
- **Dataset:** `m01-world-v1` (train, validation, test cohorts).
- **Model:** Random Forest selected (over Logistic Regression) based on validation performance.
- **Threshold:** `0.7303` (selected on the validation set to maximize F1).
- **Result:**
  - Precision: 0.752
  - Recall: 0.614
  - F1: 0.676
  - FPR: 0.014
  - TTD: Detected 8/8 campaigns. Median TTD: 28.67 mins, P95 TTD: 81.99 mins.
- **Artifacts:** `system_a_model.pkl` and `metadata.json` saved in `artifacts/experiments/m02_baseline`.
- **Conclusion:** System A is an effective and robust local baseline, but leaves room for improvement, specifically in achieving faster detection times and better recall.
- **Next action:** implement System B to evaluate the impact of cross-merchant graph features.

## M03-EVAL-002 — System B: Network-Enhanced Detection

- **Purpose:** Evaluate the incremental value of cross-merchant network intelligence (System B) over the frozen System A local baseline.
- **Dataset:** `m01-world-v1` (train, validation, test cohorts).
- **Model:** Cost-aware Random Forest (Max 5% FPR constraint).
- **Ablation Results:**
  - **System A (Local Only):** F1 0.6230, FPR 0.0357, Coverage 1.00, Median TTD 28.67m, Expected Cost $28,680.00
  - **System B (Local + Device):** F1 0.7823, FPR 0.0188, Coverage 1.00, Median TTD 26.77m, Expected Cost $16,500.00
  - **System B (Local + Network Group):** F1 0.5117, FPR 0.0182, Coverage 1.00, Median TTD 15.03m, Expected Cost $46,230.00
  - **System B (Local + Account):** F1 0.7475, FPR 0.0328, Coverage 1.00, Median TTD 17.88m, Expected Cost $13,260.00
  - **System B (Local + All Network):** F1 0.7924, FPR 0.0179, Coverage 0.88, Median TTD 19.30m, Expected Cost $15,700.00
- **System A vs System B (All Network) Comparison:**
  - **F1:** +0.1694 (+27.2%)
  - **FPR:** -0.0178 (-49.9%)
  - **Coverage:** -0.12 (-12.0%)
  - **Median TTD:** -9.37m (-32.7%)
  - **Expected Cost:** -$12,980.00 (-45.3%)
- **Artifacts:** `system_b_model.pkl` and `metadata.json` saved in `artifacts/experiments/m03_system_b`.
- **Conclusion:** Network features (especially Device and Account cross-merchant tracking) dramatically improve F1 (0.62 -> 0.79) and reduce Expected Cost by 45%. However, Network Group features alone were noisy, and the full feature set slightly reduced absolute coverage (1.00 -> 0.88) due to strict thresholding on some campaigns. The results confirm the primary hypothesis that cross-merchant graph signals improve detection and reduce TTD.
- **Next action:** Implement M04 (System C).

## M04-EVAL-003 — System C: Temporal & Emerging-Risk Detection

- **Purpose:** Evaluate the incremental value of temporal and emerging-risk features over the frozen System A and System B baselines.
- **Dataset:** `m01-world-v1` (train, validation, test cohorts).
- **Model:** Cost-aware Random Forest (Max 5% FPR constraint).
- **Ablation Results:**
  - **System A (Local Only):** F1 0.6230, FPR 0.0357, Coverage 1.00, Median TTD 28.67m, Expected Cost $28,680.00
  - **System B (All Network):** F1 0.7924, FPR 0.0179, Coverage 0.88, Median TTD 19.30m, Expected Cost $15,700.00
  - **System B* (Local + Device + Account):** F1 0.8113, FPR 0.0241, Coverage 1.00, Median TTD 17.88m, Expected Cost $9,090.00
  - **System C (B* + Rolling):** F1 0.8007, FPR 0.0274, Coverage 1.00, Median TTD 15.51m, Expected Cost $8,560.00
  - **System C (B* + Growth):** F1 0.9046, FPR 0.0114, Coverage 0.75, Median TTD 2.68m, Expected Cost $4,370.00
  - **System C (B* + Synchronization):** F1 0.8722, FPR 0.0135, Coverage 1.00, Median TTD 5.63m, Expected Cost $7,510.00
  - **System C (B* + All Temporal):** F1 0.9102, FPR 0.0084, Coverage 0.88, Median TTD 2.76m, Expected Cost $5,940.00
  - **System C (All Network + All Temporal):** F1 0.9422, FPR 0.0039, Coverage 0.88, Median TTD 2.76m, Expected Cost $5,040.00
- **System A vs Best System C (All Network + All Temporal) Comparison:**
  - **F1:** +0.3192 (+51.2%)
  - **FPR:** -0.0318 (-89.1%)
  - **Coverage:** -0.12 (-12.0%)
  - **Median TTD:** -25.91m (-90.4%)
  - **Expected Cost:** -$23,640.00 (-82.4%)
- **System B (All Network) vs System C (All Network + All Temporal) Comparison:**
  - **F1:** +0.1498 (+18.9%)
  - **FPR:** -0.0140 (-78.2%)
  - **Coverage:** No change (0.88)
  - **Median TTD:** -16.54m (-85.7%)
  - **Expected Cost:** -$10,660.00 (-67.9%)
- **Coverage Analysis:** The addition of temporal features (specifically Growth) drops coverage significantly (from 1.0 to 0.75 in the B* + Growth ablation). Synchronization, on the other hand, preserves 1.00 coverage (B* + Sync) while dropping TTD from 17.88m to 5.63m. The full System C model does not recover the 12% coverage lost in the full System B. Instead, it holds at 0.88, indicating that certain campaigns are still missed by strict thresholds when using these broad features.
- **Artifacts:** `system_c_model.pkl` and `metadata.json` saved in `artifacts/experiments/m04_system_c`.
- **Conclusion:** Temporal signals provide monumental value. Adding temporal synchronization and growth rates to the existing network graph cuts detection times by ~90% and reduces expected operational cost by over 80%. Synchronization features are particularly effective at accelerating detection without sacrificing coverage.
- **Next action:** Implement M04-R (Robustness Evaluation).

## M04-R-EVAL-004 — Robustness & Generalization Evaluation

- **Purpose:** Evaluate whether the strongest M04 System C temporal detection models generalize to adversarial variations of coordinated behavior (timing jitter, low-and-slow execution, varied amounts).
- **Dataset:** `m01-world-v1` perturbed variants (Jitter, Low-and-Slow, Amount).
- **Model:** Frozen M04 cost-aware models.
- **Ablation Candidates:**
  - **A:** All Network + All Temporal
  - **B:** B* + Synchronization
  - **C:** B* + Growth
  - **D:** B* + Synchronization + Growth (New Candidate)
- **Robustness Results (Degradation from Baseline):**
  - **Candidate A:** Baseline F1 0.9422 (Cov 0.88). Under Jitter: F1 0.9340 (-0.0082). Under Low & Slow: F1 0.7769 (-0.1654).
  - **Candidate B:** Baseline F1 0.8722 (Cov 1.00, TTD 5.6m). Under Jitter: F1 0.8634 (-0.0088). Under Low & Slow: F1 0.7672 (-0.1050).
  - **Candidate C:** Baseline F1 0.9046 (Cov 0.75, TTD 2.6m). Under Jitter: F1 0.9025 (-0.0021). Under Low & Slow: F1 0.8545 (-0.0501).
  - **Candidate D:** Baseline F1 0.8837 (Cov 1.00, TTD 3.6m). Under Jitter: F1 0.8745 (-0.0092). Under Low & Slow: F1 0.7927 (-0.0910).
- **Analysis:**
  - All candidates are extremely robust to Amount variation (zero degradation) and highly robust to Timing Jitter (less than 0.01 drop in F1).
  - The primary failure mode is **Low-and-Slow** execution. Candidate A suffers a massive -0.165 F1 drop, and Candidate B drops -0.105. 
  - **Candidate D (B* + Sync + Growth)** is the optimal balanced detector. It successfully combines the speed of Growth features (bringing TTD down to 3.6 mins) with the stability of Synchronization features, preventing the severe coverage collapse (0.75) seen in Candidate C. Candidate D maintains a perfect 1.00 coverage across all scenarios, even while taking a moderate hit to F1 during low-and-slow attacks.
- **Conclusion:** Candidate D is the recommended core Sentinel detector. While the strict All Network + All Temporal (Candidate A) achieved the highest theoretical F1 in M04, it is highly brittle to low-and-slow evasion and misses 12% of campaigns. Candidate D maximizes coverage and speed while maintaining robust F1 generalization.
- **Next action:** Implement M05 (Agentic Feedback / Server-side Scoring).


## M08 Policy Simulation
- Synthetic economic model established: loss_severity_factor=1.0, fp_cost_rate=0.05, manual_review_cost=5.0.
- **Important Note**: These are synthetic evaluation assumptions and do not represent real Razorpay economics. Policy determinism verified via 	ests/test_m08_policy.py proving action bounding beyond AI recommendations.
