# Sentinel Mesh Threat Model

## M08 Updates
The LLM provides evidence synthesis and a recommendation; the deterministic policy engine retains authority over permitted actions. 

This protects against:
1. **Prompt Injection**: A malicious merchant payload attempting to command the AI to "release funds" will fail because the API uses the deterministic Policy Engine to choose actions.
2. **LLM Hallucinations**: If the LLM generates a mathematically incorrect or ungrounded inference, the deterministic engine catches it via Grounding Metrics or Economic Thresholds.
