# Limitations

## 1. Synthetic M01 Environment
M01 is a controlled synthetic environment and is not a representative production fraud population. It is designed to test specific hypotheses about coordinated abuse, not to reflect the exact distribution of real-world transactions.

## 2. External Benchmark Scope
The external benchmark (M12) tests transaction-level classification only. It does **not** validate:
- Candidate D's M01-specific network features.
- Coordinated-abuse graph detection.
- Merchant Spike behavior.
- Agent investigation quality.

## 3. Feature Mismatch
External benchmark features differ significantly from M01 features. Do not compare their numbers as if they are measurements on the same task or dataset.

## 4. Calibration
Probability calibration (M13):
- Is an analytical experiment.
- Uses M01 validation data for fitting.
- Is **not** integrated into the PolicyEngine.
- May degrade under prior or distribution shifts in a real-world setting.

## 5. Robustness
Adversarial attacks evaluated in M14 are synthetic perturbations. They cover selected scenarios only (e.g., timing jitter, low-and-slow) and do **not** prove resilience to all real-world evasion tactics.

## 6. Early Warning
The Early Warning detector:
- Can increase investigation candidates.
- Has a measured false-positive trade-off.
- Is **not** a proof of autonomous fraud blocking.
- Should be closely monitored in any real-world deployment.

## 7. LLM Limitations
The Gemini-powered LLM agent:
- Assists investigation by synthesizing evidence.
- Can be unavailable (requiring fallback mechanisms).
- Requires strict evidence grounding to prevent hallucinations.
- Is **not** responsible for case identity or grouping.
- Does **not** replace deterministic controls or the PolicyEngine.

## 8. Policy Layer
The PolicyEngine remains strictly deterministic. Its thresholds and cost assumptions are engineering assumptions used for evaluation, not universal industry standards.

## 9. Cost Assumptions
Benchmark cost figures depend on explicitly stated assumptions (e.g., fixed manual review costs, specific false positive penalties) and are **not** real-world financial estimates.

## 10. Data / Deployment
The current implementation has several deployment limitations:
- Relies on a local SQLite database (`sentinel.db`).
- Uses synthetic/generated datasets.
- Operates as a single-instance/demo architecture.
- Lacks production-scale load testing.
Do not claim production readiness based on this prototype.

## 11. Evaluation Scope
The project demonstrates a controlled prototype and reproducible evaluation methodology. It is **not** a certified production fraud detection system.

## 12. Honest Summary
The primary value of the Sentinel Mesh project lies in its end-to-end architecture, controlled evaluation methodology, robustness analysis, and explicit treatment of failure modes (like AI degradation). It does **not** make a claim of universal, production-ready fraud-detection accuracy.
