# Judge Pitch Material

## 1. 30-SECOND PITCH
**Problem:** Coordinated synthetic payment abuse is incredibly difficult to detect because individual transactions often look benign in isolation.
**Solution:** Sentinel Mesh is an experimental risk-operations platform that combines merchant-local, cross-merchant network, and temporal signals to detect these clusters earlier.
**Differentiator:** We pair a highly optimized detection model (Candidate D) with a Gemini-powered AI investigation agent, all wrapped in a strict, deterministic Policy Engine that prevents AI hallucinations from taking arbitrary financial actions.
**Outcome:** We demonstrate significantly reduced time-to-detection for coordinated attacks, a robust analyst workflow, and graceful degradation when AI fails.

## 2. 2-MINUTE PITCH
**Problem:** Modern fraud is coordinated. Attackers distribute their activity across multiple merchants, devices, and accounts. Traditional, merchant-local models miss this because individual transactions look weak.
**Solution:** Sentinel Mesh solves this by combining transaction data with network graph relationships, temporal synchronization, and growth signals.
**Detection:** Our core model, Candidate D, detects these clusters. We also run an Early Warning detector in parallel to catch low-and-slow attacks, and a Merchant Spike detector for sudden volume anomalies.
**Operations:** To prevent alert fatigue, we deterministically group these signals into parent cases using a 24-hour rolling window.
**Investigation:** Analysts don't have to sift through raw data. Our Gemini-powered AI agent investigates the case, synthesizes the evidence, and presents a grounded dossier alongside a Network Evidence Graph.
**Safety:** We don't let AI make financial decisions autonomously. A deterministic Policy Engine evaluates the quantitative scores and analyst dispositions to enforce bounded actions. If the AI fails, the system gracefully falls back to deterministic rules.
**Validation:** We've rigorously evaluated this. We benchmarked our transaction-level capabilities on an external dataset, performed leakage-safe probability calibration, and subjected the models to adversarial robustness testing, specifically measuring and mitigating weaknesses against low-and-slow attacks.

## 3. TECHNICAL ARCHITECTURE TALK
Sentinel Mesh is split into a runtime pipeline and offline evaluation.
At runtime, we extract causal features across three dimensions: **local** (merchant-specific velocity), **network** (cross-merchant device/account graphs), and **temporal/growth** (synchronization metrics).
These features feed into **Candidate D**, our primary cost-aware Random Forest model. Running in parallel is the **Early Warning** detector, which enriches cases before they cross the strict Candidate D threshold, and the **Merchant Spike** detector for volume anomalies.
Instead of firing isolated alerts, we use **case aggregation** to deterministically group signals by entity and time into a parent case.
For **investigation**, a Gemini LLM queries the case data to build a structured dossier. This is visualized alongside a **Network Evidence Graph**.
Crucially, the final decision rests with the **PolicyEngine**, a deterministic layer that bounds financial actions based on risk scores and analyst input, ensuring safety even if the AI hallucinates or fails.
Offline, we rigorously evaluate these models using external benchmarks, probability calibration, and adversarial robustness testing.

## 4. KEY NUMBERS
*Note: These are verified values from our offline evaluation artifacts.*

**M12 External Benchmark (Kaggle Dataset):**
- 284,807 rows (492 fraud cases)
- PR-AUC: 0.7958
- Precision: 0.8250
- Recall: 0.8148
- F1: 0.8199

**M13 Probability Calibration:**
- Candidate D selected method: Isotonic
- External benchmark selected method: Isotonic
- *Honest Note:* Candidate D's calibrated TEST Brier score (0.011194) was slightly worse than its raw Brier score (0.010454), though Expected Calibration Error (ECE) improved.

**M14 Adversarial Robustness:**
- Clean F1: 0.8837
- Low-and-Slow 24x F1: 0.4123 (TTD: 247.0m)
- Early Warning mitigation 24x TTD: 116.2m (an improvement of 130.8m)
- Selected validation FPR target: <=0.5%
- Incremental clean FPs: ~+14 to +15 depending on evaluation context.

**M15 Alert Aggregation:**
- Deterministic 24h entity+temporal grouping with duplicate signal suppression.

## 5. WHAT THE PROJECT PROVES
- A controlled evaluation of coordinated-abuse detection using the synthetic M01 dataset.
- A reproducible transaction-level external benchmark.
- A leakage-safe probability calibration experiment.
- A targeted adversarial robustness evaluation.
- A measured improvement against low-and-slow behavior using parallel Early Warning.
- A working, end-to-end risk-operations workflow with AI integration and deterministic safety.

## 6. WHAT IT DOES NOT PROVE
- Universal real-world fraud accuracy (M01 is synthetic).
- Production-scale throughput or load capacity.
- Robustness against every possible real-world attacker.
- Calibrated real-world probability validity.
- External validation of M01-specific network features (the external benchmark lacked network data).
- Autonomous AI decision making (the PolicyEngine is strictly deterministic).

## 7. LIKELY JUDGE QUESTIONS & ANSWERS

**1. Why synthetic M01?**
Real-world coordinated fraud data is highly sensitive, proprietary, and lacks perfect ground truth. M01 provides a controlled, leakage-audited environment to isolate and measure the impact of specific network and temporal features.

**2. Why use an external benchmark?**
To prove that our underlying modeling pipeline (feature extraction, thresholding, evaluation) is sound and capable of achieving strong results on a known, real-world transaction-level dataset.

**3. Why can't Candidate D be evaluated directly on the external dataset?**
Candidate D relies heavily on cross-merchant network graph features (devices, accounts). The external Kaggle dataset is anonymized and lacks these cross-entity relationship identifiers.

**4. Why isn't the calibrated probability used by PolicyEngine?**
Calibration is an analytical experiment. In a real-world setting, calibration can degrade quickly under distribution shifts. The PolicyEngine relies on robust, raw risk scores and deterministic rules for safety.

**5. What happens when the LLM fails?**
The system degrades gracefully. The UI displays an `AI_UNAVAILABLE` state, but the deterministic PolicyEngine and manual analyst workflows remain fully functional.

**6. Can attackers evade the detector?**
Yes. Our M14 robustness testing showed that while the model is robust to timing jitter, it is susceptible to severe "low-and-slow" attacks.

**7. What was the biggest weakness found?**
Low-and-slow execution. When attackers stretch their activity over a long period, short-term velocity features collapse, significantly delaying Time-to-Detection (TTD).

**8. What did you do about low-and-slow?**
We implemented an Early Warning detector that runs in parallel. It uses longer-horizon network features to flag suspicious entities for investigation earlier, improving TTD by over 130 minutes in our 24x slowed attack scenario.

**9. Why use deterministic case grouping instead of an LLM?**
Safety and determinism. LLMs are prone to hallucination and inconsistency. Grouping alerts by entity and time must be perfectly reliable to prevent alert fatigue and ensure auditability.

**10. How are false positives controlled?**
Through strict, cost-aware thresholding selected purely on validation data. We optimize for a maximum False Positive Rate (e.g., 5% for Candidate D, 0.5% for Early Warning) before evaluating on the test set.

**11. What prevents leakage?**
Strict temporal cohort separation (Train/Val/Test). Features are extracted causally—no future data can influence past predictions. Ground truth labels are never exposed to the feature pipeline.

**12. Is this production-ready?**
No. It is an experimental prototype demonstrating an architecture. It uses a local SQLite database and synthetic data, and has not undergone production load testing.

**13. What would you build next?**
Integration with a real-time graph database for scalable network feature extraction, and testing against a real-world, cross-merchant dataset.

**14. Why is this different from a standard fraud classifier?**
Standard classifiers look at transactions in isolation. Sentinel Mesh builds a cross-merchant graph and uses temporal synchronization features to detect the *coordination* between seemingly unrelated transactions.

**15. How does the system handle coordinated activity across multiple entities?**
The Network Evidence Graph and temporal features identify when disparate accounts or devices synchronize their behavior across multiple merchants, flagging the cluster rather than just the individual nodes.

## 8. HONEST LIMITATIONS ANSWERS
If challenged on accuracy: "We do not claim universal real-world accuracy. Our high F1 scores in M04 are a product of the controlled synthetic environment designed to test specific hypotheses. The value is in the architecture and the robust evaluation methodology, not the absolute synthetic numbers."

## 9. DIFFERENTIATORS
- **Coordinated/Network Intelligence:** Moving beyond isolated transaction scoring.
- **Explicit Adversarial Evaluation:** We actively tried to break our own model (M14) and measured the degradation.
- **Low-and-Slow Diagnosis + Mitigation:** We didn't just find a weakness; we implemented and measured a specific mitigation (Early Warning).
- **Deterministic Safety Layer:** We use GenAI for investigation, but strictly bound its actions with a deterministic PolicyEngine.
- **Risk-Operations Workflow:** A complete end-to-end system from detection to analyst disposition, not just a Jupyter notebook.

## 10. CLOSING STATEMENT
"Sentinel Mesh is not a silver bullet for all fraud, nor is it a production-ready enterprise system today. What it *is* is a rigorous, end-to-end demonstration of how to build a modern risk-operations platform. It proves that by combining cross-merchant network intelligence with grounded AI investigation—and wrapping it all in a deterministic safety layer—we can detect coordinated abuse faster and empower analysts, while remaining honest about our limitations and failure modes."
