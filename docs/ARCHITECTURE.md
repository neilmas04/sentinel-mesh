# Architecture

## 1. Architecture Overview
Sentinel Mesh is structured into a runtime pipeline for live detection and risk operations, and an offline architecture for evaluation and experimentation. The system relies on causal feature extraction, deterministic aggregation, and a bounded Policy Engine to ensure safety and transparency, while leveraging an LLM for agentic investigation.

## 2. Runtime Pipeline
The end-to-end flow for a transaction at runtime is as follows:
1. **Transaction:** A new transaction enters the system.
2. **Causal Feature Extraction:** Features are extracted using strictly causal, point-in-time data.
3. **Candidate D:** The transaction is scored by the primary Candidate D risk model.
4. **Early Warning:** The EarlyWarningDetector runs in parallel to identify emerging threats.
5. **Merchant Spike:** Where applicable, merchant-level anomalies are detected.
6. **Deterministic Case Aggregation:** Signals are grouped deterministically into a parent Risk Case.
7. **Risk Case:** The aggregated case is presented to the analyst.
8. **Agentic Investigation:** The AI agent can be triggered to investigate the case.
9. **Evidence:** The agent collects and synthesizes evidence into a structured dossier.
10. **Network Evidence Graph:** A visual graph of connected entities is generated.
11. **Analyst Disposition:** An analyst reviews the case, notes, and evidence, and provides a disposition.
12. **PolicyEngine:** The deterministic Policy Engine evaluates the case and disposition.
13. **Action:** A bounded financial action (e.g., HOLD, MONITOR) is executed.

## 3. Feature Layers
Features are extracted across multiple dimensions:
- **Local:** Merchant-local decision-time features (e.g., amount, local account velocity).
- **Network:** Cross-merchant relationship features (e.g., device graphs, account interaction graphs).
- **Temporal:** Time-based sequences and synchronization metrics.
- **Growth/Persistence:** Rates of change and emerging cluster behaviors.

## 4. Candidate D
Candidate D is the core detection model selected during the M04-R robustness evaluation. It is a cost-aware Random Forest model that balances speed and coverage by combining network synchronization and growth features. It provides the primary transaction-level risk score used for case generation.

## 5. Early Warning
The Early Warning detector runs in parallel with Candidate D. It uses causal features and validation-selected thresholds to identify suspicious patterns before they cross the strict Candidate D threshold. It creates or enriches investigation candidates but does **not** auto-block transactions, serving instead to surface emerging threats for review.

## 6. Merchant Spike
The Merchant Spike detector identifies sudden bursts of activity at specific merchants. It maintains a bucket-level timeline, comparing baseline historical volume against live observations. When HIGH or CRITICAL signals are generated, they are integrated into the deterministic case aggregation pipeline.

## 7. Case Aggregation
To prevent alert fatigue, individual signals (from Candidate D, Early Warning, or Merchant Spike) are grouped into a **parent case**.
- **Deterministic Grouping:** Cases are grouped deterministically by entity (e.g., device, account) and time.
- **Duplicate Protection:** Duplicate signals for the same entity within the grouping window are merged.
- **24-Hour Window:** Signals are aggregated over a 24-hour rolling window.
- **Closed Cases:** Once a case is closed, new signals for that entity will generate a new case rather than reopening the closed one.

## 8. Investigation
The Gemini-powered AI agent assists in the investigation process by querying tools, synthesizing evidence, and generating a structured dossier.
- **LLM Assists:** The LLM is an investigative assistant, not a decision-maker.
- **No Case Grouping:** The LLM does **not** determine case identity or grouping; this is handled deterministically by the aggregation layer.
- **Deterministic Policy:** The Policy Engine remains fully deterministic, bounding the actions that can be taken regardless of the LLM's output.

## 9. Analyst Workflow
The platform provides a structured workflow for human analysts:
- **Status:** Cases track their lifecycle status (e.g., OPEN, INVESTIGATING, CLOSED).
- **Disposition:** Analysts can apply a final disposition (e.g., TRUE_POSITIVE, FALSE_POSITIVE).
- **Analyst Notes:** Analysts can append notes to the case.
- **Audit Log:** All status changes, dispositions, and notes are immutably recorded in the case's audit trail.

## 10. AI Failure Fallback
The system is designed for graceful degradation. If the Gemini API is unreachable, times out, or returns an error:
- The system enters an `AI_UNAVAILABLE` or `FALLBACK MODE ACTIVE` state.
- Deterministic behavior remains fully available.
- Cases can still be aggregated, viewed, and dispositioned manually by analysts, and the Policy Engine continues to enforce rules based on quantitative risk scores.

## 11. Policy Layer
The Policy Engine is the deterministic action layer. It evaluates the quantitative case features (Risk Score, Amount), the analyst's disposition, and the LLM's grounded dossier (if available). It enforces a strict ruleset based on synthetic economic models (expected fraud loss vs. false positive cost) to return a bounded action (MONITOR, MANUAL_REVIEW, ENHANCED_VERIFICATION, or HOLD), preventing arbitrary or hallucinated actions.

## 12. Offline Evaluation Architecture
The offline architecture is strictly separated from the runtime pipeline. It includes:
- **External Benchmark:** Evaluating transaction-level capability against external datasets.
- **Calibration:** Analytical probability calibration of model outputs.
- **Adversarial Robustness:** Testing models against synthetic perturbations (jitter, low-and-slow).
- **Early-Warning Regression:** Offline experiments to tune and validate the Early Warning detector.

## 13. Security / Integrity Boundaries
- **No Ground Truth at Runtime:** Labels and scenarios are never accessible to the feature extraction or runtime pipeline.
- **No Future Data:** Feature extraction is strictly causal; no future data can leak into past predictions.
- **Environment Secrets:** API keys and credentials are kept in `.env` and never committed.
- **Deterministic Grouping:** Case aggregation and policy decisions are deterministic, preventing AI hallucinations from altering core system logic.
- **Auditability:** All case actions and state changes are logged for auditability.
