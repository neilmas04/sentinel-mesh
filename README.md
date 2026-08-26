# Sentinel Mesh

Sentinel Mesh is an experimental, defensive payment-risk prototype. It tests whether merchant-local, cross-merchant relationship, and temporal signals can identify coordinated synthetic payment abuse earlier while controlling false positive cost. It also demonstrates an autonomous, AI-driven risk investigation agent powered by Gemini, which synthesizes cross-merchant evidence to justify risk decisions transparently.

## Project Overview & Objectives

- **M01 - Deterministic World Generation:** A robust temporal dataset simulating organic and synthetic fraudulent transactions across a merchant network.
- **M02 - M04 Modeling:** Progressive evaluations of baseline, network-graph, and temporal ML models for Time-to-Detection (TTD).
- **AI Agent Integration:** A Gemini 2.5 powered risk investigator that securely interfaces with Sentinel Mesh tools to collect evidence and output a structured, grounded dossier.
- **Field-Aware Grounding Validation:** Strict deterministic checks ensure that the LLM's claims directly map to factual evidence fields without hallucination.
- **Policy Engine:** Translates grounded LLM risk assessments into bounded financial actions (e.g., Hold, Enhanced Verification, Monitor).

## Setup & Installation

Create a Python 3.12 virtual environment, install the pinned dependencies, and set up the necessary environment variables.

```powershell
# Create and activate environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
python -m pip install -r requirements.txt

# Environment Setup
cp .env.example .env
# Edit .env and insert your GOOGLE_API_KEY
```

## Usage

### Running the Investigation Agent

You can trigger a full end-to-end investigation for a specific risk case (e.g., a suspicious device):

```powershell
python -m src.agent.demo_investigation
```

This will run the agent against the deterministic evidence cluster, invoke Gemini for structured risk analysis, and process the result through the Field-Aware Grounding Validator.

### Running the Simulation Pipeline

To recreate the deterministic dataset from scratch (WARNING: This will overwrite `data/generated`):

```powershell
python -m src.simulation --seed 20260824
```

## End-to-End (E2E) Validation Details

- **Deterministic Tests:** Full coverage is provided for the feature extraction, models, agent reasoning loop, and policy layers. Run `python -m pytest -v` to execute all tests.
- **Grounding Validation:** The agent's output is rigorously checked using a field-aware validation approach. Float regression (e.g., distinguishing 844.29 from 844.39) and exact ID matching ensure that Gemini's output is purely factual.
- **AI Degradation:** The pipeline implements a graceful degradation model. If the Gemini API is unreachable or times out, the system automatically falls back to deterministic rule-based policies.
