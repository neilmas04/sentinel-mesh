# Sentinel Mesh

Sentinel Mesh is an experimental, defensive payment-risk prototype. It tests
whether merchant-local, cross-merchant relationship, and temporal signals can
identify coordinated synthetic payment abuse earlier while controlling false
positive cost. It does not claim production performance or knowledge of
Razorpay's internal systems.

## Current milestone

**M01 — deterministic synthetic payment world.** The model, API, Gemini
verifier, policy engine, and dashboard are intentionally not part of this
milestone's execution path.

## Generate the M01 dataset

Create a Python 3.12 virtual environment, install the pinned dependencies, and
run:

```powershell
python -m pip install -r requirements.txt
python -m src.simulation --seed 20260824
python -m unittest discover -s tests -v
```

The generator itself deliberately uses the Python standard library. It writes
a reproducible versioned dataset under `data/generated/m01-world-v1/`:

- `cohorts/<train|validation|test>/transactions.csv` — model-safe inputs only
- `entities/` — persistent merchants, accounts, devices, and network groups
- `ground_truth/` — event labels and campaign manifests; never model inputs
- `manifests/` — configuration, temporal split, summary, and leakage report

See `docs/DATA_GENERATION.md` and `docs/EVALUATION_PROTOCOL.md` before using
the data in a model.
