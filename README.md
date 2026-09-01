# Sentinel Mesh

## 1. Project Overview
Sentinel Mesh is an experimental, defensive payment-risk prototype and risk-operations platform. It is designed for detecting, investigating, and responding to suspicious and coordinated synthetic transaction activity. It tests whether merchant-local, cross-merchant relationship, and temporal signals can identify coordinated abuse earlier while controlling false positive cost. It also demonstrates an autonomous, AI-driven risk investigation agent powered by Gemini, which synthesizes cross-merchant evidence to justify risk decisions transparently.

## 2. Core Capabilities
- **Candidate D transaction risk scoring:** The core detection model balancing speed and coverage.
- **Local/network/temporal features:** Causal feature extraction across merchant-local, cross-merchant graph, and temporal/emerging-risk dimensions.
- **Merchant Spike detection:** Identifies sudden bursts of activity at specific merchants.
- **Merchant Spike timeline visualization:** Visualizes baseline vs. live observation metrics.
- **EarlyWarningDetector:** Runs in parallel to enrich investigation candidates using causal features and validation-selected thresholds.
- **Parent/child alert aggregation:** Deterministic entity and temporal grouping of signals into parent cases.
- **Related signals:** Surfacing related alerts and events within a case.
- **Analyst disposition:** Workflow for analysts to review, add notes, and disposition cases.
- **Audit trail:** Immutable logging of case status changes and actions.
- **Agentic investigation:** A Gemini-powered risk investigator that securely interfaces with Sentinel Mesh tools to collect evidence.
- **Network Evidence Graph:** Visual representation of the interconnected entities involved in a risk case.
- **AI failure fallback:** Graceful degradation to deterministic rule-based policies if the AI is unavailable.
- **Deterministic PolicyEngine:** Translates risk assessments into bounded financial actions (e.g., Hold, Enhanced Verification, Monitor).
- **External transaction fraud benchmark:** Evaluation against external datasets to validate transaction-level capabilities.
- **Probability calibration analysis:** Ensures risk scores are well-calibrated probabilities.
- **Adversarial robustness evaluation:** Testing the models against synthetic perturbations like timing jitter and low-and-slow execution.

## 3. Runtime Architecture
The Sentinel Mesh architecture is split into runtime detection/investigation and offline evaluation/experimentation.
At runtime, transactions flow through causal feature extraction, are scored by Candidate D and Early Warning detectors, and are aggregated into Risk Cases. The AI Agent can then investigate these cases, presenting evidence and a Network Evidence Graph to an analyst, who can disposition the case. A deterministic Policy Engine ultimately decides the bounded action.
For a detailed breakdown, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 4. Setup
Create a Python 3.12 virtual environment, install the pinned dependencies, and set up the necessary environment variables.

### Backend
Open a PowerShell terminal and run:
```powershell
cd sentinel-mesh
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

### Frontend
Open a new PowerShell terminal and run:
```powershell
cd sentinel-mesh\frontend
npm install
npm run dev
```
*(Note: Depending on your Windows environment, you may need to invoke `npm run dev` through the actual npm executable, e.g., `& "C:\Program Files\nodejs\npm.cmd" run dev`)*

## 5. Environment Variables
Copy the example environment file and configure it:
```powershell
cp .env.example .env
```
Edit `.env` and insert your `GOOGLE_API_KEY`.
**Important:** Never commit your `.env` file. It contains sensitive keys and is ignored by Git.

## 6. Running the Demo
The platform includes a frontend dashboard to visualize the risk operations workflow. The main UI flow is:
1. **Dashboard:** View active cases and system status.
2. **Normal Traffic:** Run a benign synthetic demo scenario to observe baseline behavior.
3. **Emerging Cluster:** Run a scenario simulating coordinated abuse.
4. **Risk Case:** Open the generated high-risk case from the dashboard.
5. **Related Signals:** Review the individual signals that were aggregated into the case.
6. **Network Evidence Graph:** Explore the visual graph of connected entities.
7. **Start Investigation:** Trigger the AI agent to analyze the evidence.
8. **Evidence:** Review the structured dossier and grounded claims produced by the AI.
9. **AI Failure fallback:** Simulate an AI failure to observe the deterministic fallback mode.
10. **Evaluation:** View offline evaluation metrics and benchmark results.

## 7. Testing
To run the backend deterministic tests:
```powershell
.\venv\Scripts\python -m pytest
```

To build the frontend for production:
```powershell
cd frontend
npm run build
```

## 8. Evaluation
- **M01:** Deterministic generation of a synthetic world dataset with organic and fraudulent transactions.
- **Candidate D:** The optimal balanced detector identified in M04-R, combining network synchronization and growth features.
- **External Benchmark:** Evaluates the transaction-level capability of the models on external datasets.
- **Calibration:** Analytical probability calibration to ensure reliable risk scores.
- **Robustness:** Synthetic adversarial perturbations (jitter, low-and-slow) to test model generalization.
Detailed evaluation reports and artifacts are available in the `docs/` and `artifacts/` directories.

## 9. Security / Data Handling
- `.env` is ignored by Git to prevent leaking secrets.
- `sentinel.db` (the local SQLite database) is ignored.
- External benchmark datasets are ignored.
- Generated data and experiment artifacts in `data/` and `artifacts/` are not committed.
- There are no real credentials or PII in the repository.

## 10. Limitations
The system operates on synthetic data and has specific constraints regarding its evaluation and real-world applicability. For a full list of limitations, see [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## 11. Repository Structure
```text
sentinel-mesh/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── artifacts/          # Ignored: Model artifacts and evaluation plots
├── data/               # Ignored: Generated synthetic datasets
├── docs/               # Documentation (Architecture, Experiments, etc.)
├── frontend/           # React + Vite frontend application
├── src/                # Backend source code (API, Agent, Models, Simulation)
└── tests/              # Pytest test suite
```
