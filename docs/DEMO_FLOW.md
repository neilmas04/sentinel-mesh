# Sentinel Mesh Demo Flow

## DEMO PRINCIPLES
- Keep the flow deterministic where possible.
- Avoid fragile exploratory clicks.
- Do not depend on random behavior.
- Do not expose secrets (e.g., `.env` contents).
- Do not require regenerating experiments during the demo.
- Use already-generated evaluation artifacts.

## DEMO SAFETY
- **Backend Required:** Yes, the backend must be running (`python -m uvicorn src.api.main:app`).
- **Frontend Required:** Yes, the frontend must be running (`npm run dev`).
- **Existing Cases:** Existing cases in the dashboard can be reused if they match the scenario, but it is cleaner to generate fresh ones using the Simulation Controls.
- **Avoiding Unnecessary Data:** Only click the simulation buttons once per scenario to avoid flooding the database.
- **Recovery:** If a case already exists or the dashboard is cluttered, you can restart the backend (which uses a local SQLite DB) or simply focus on the most recently generated case at the top of the list.

## WHAT NOT TO DEMO
- Fragile internal scripts or raw database manipulation.
- Exploratory diagnostic scripts (e.g., `diagnose_output.txt`).
- Unnecessary terminal work (keep the focus on the UI).
- Unsupported capabilities (e.g., claiming the AI makes autonomous blocking decisions).

## DEMO TIMING
- **60-second compressed version:** Dashboard -> Emerging Cluster -> Open Case -> Start Investigation -> Show Evidence -> Conclude.
- **3-minute standard version:** Follow the full 25-step flow below at a brisk pace.
- **5-minute technical version:** Follow the full flow, pausing to explain the architecture (Candidate D, Early Warning) and offline evaluation metrics (M12, M14) in detail.

## DEMO FLOW SEQUENCE & TALK TRACK

**Story Arc:** Detect → explain → investigate → correlate → decide → recover from AI failure → evaluate.

### 1. Dashboard
- **Action:** Open the Sentinel Mesh frontend (`http://localhost:5173`).
- **Talk Track:** "Welcome to Sentinel Mesh, a risk-operations platform designed to detect and investigate coordinated synthetic payment abuse."
- **Expected Result:** The main dashboard loads, showing active cases (if any) and system status.

### 2. Explain active risk cases / risk posture
- **Action:** Point to the active cases list.
- **Talk Track:** "Here we see our active risk cases. The system aggregates individual transaction alerts into parent cases to prevent alert fatigue."

### 3. Normal Traffic
- **Action:** Click the "Normal Traffic" simulation button.
- **Talk Track:** "Let's simulate some normal, benign traffic on the network."
- **Expected Result:** A notification appears indicating normal traffic was processed. No new high-risk case is created.

### 4. Explain why no case is created
- **Action:** Wait a moment to show the dashboard remains unchanged.
- **Talk Track:** "Because this traffic lacks the temporal synchronization and cross-merchant velocity of an attack, our Candidate D model correctly ignores it, keeping the analyst queue clean."

### 5. Emerging Cluster
- **Action:** Click the "Emerging Cluster" simulation button.
- **Talk Track:** "Now, let's simulate a coordinated synthetic abuse cluster."
- **Expected Result:** A new high-risk case appears at the top of the dashboard.

### 6. Open Risk Case
- **Action:** Click on the newly created Risk Case to open the Case Detail view.
- **Talk Track:** "The system has detected the attack and deterministically grouped the alerts into a single parent case."
- **Expected Result:** The Case Detail page loads.

### 7. Show Risk Profile
- **Action:** Point to the Risk Profile section at the top.
- **Talk Track:** "Here we see the overall risk score and the primary entity involved."

### 8. Show Model Version
- **Action:** Point to the model version displayed in the Risk Profile.
- **Talk Track:** "Notice this was flagged by Candidate D, our core detection model optimized for speed and coverage."

### 9. Show Related Signals
- **Action:** Scroll to the Related Signals section.
- **Talk Track:** "Instead of isolated alerts, we see a timeline of related signals."

### 10. Show Early Warning / Candidate D evidence
- **Action:** Point out the specific signals in the list.
- **Talk Track:** "You can see Early Warning signals that fired in parallel to enrich the case, alongside the definitive Candidate D triggers and Merchant Spike anomalies."

### 11. Show Network Evidence Graph
- **Action:** Scroll to the Network Evidence Graph.
- **Talk Track:** "This graph visually correlates the cross-merchant relationships—devices, accounts, and merchants—that form the synthetic cluster."

### 12. Start Investigation
- **Action:** Click the "Start Investigation" button.
- **Talk Track:** "To understand this complex web, we trigger our Gemini-powered AI agent to investigate the evidence."
- **Expected Result:** A loading state appears while the agent processes.

### 13. Show grounded evidence
- **Action:** Once the investigation completes, review the generated AI Dossier.
- **Talk Track:** "The LLM synthesizes the cross-merchant evidence into a readable dossier. Crucially, this output is strictly grounded against factual data to prevent hallucinations."

### 14. Show Audit Log
- **Action:** Scroll down to the Audit Log.
- **Talk Track:** "Every action, from case creation to AI investigation, is immutably recorded in the audit trail."

### 15. Show Analyst Disposition
- **Action:** Select a disposition (e.g., TRUE_POSITIVE) and add a note, then click Submit.
- **Talk Track:** "The analyst reviews the AI's findings and provides a final disposition."
- **Expected Result:** The case status updates to CLOSED.

### 16. Return to Dashboard
- **Action:** Click the back button or dashboard link.
- **Talk Track:** "Let's return to the dashboard to demonstrate our safety fallbacks."

### 17. Trigger AI Failure
- **Action:** Click the "AI Failure" simulation button.
- **Talk Track:** "What happens if the LLM goes down? We simulate an AI failure scenario."
- **Expected Result:** A new case is generated, but with an AI failure flag.

### 18. Show AI_UNAVAILABLE / FALLBACK MODE ACTIVE
- **Action:** Open the new case and click "Start Investigation".
- **Talk Track:** "When we try to investigate, the system detects the failure and enters fallback mode."
- **Expected Result:** The UI displays an `AI_UNAVAILABLE` or `FALLBACK MODE ACTIVE` message.

### 19. Show deterministic policy behavior
- **Action:** Point out that the case can still be dispositioned.
- **Talk Track:** "Even without the AI, our deterministic Policy Engine remains active, allowing analysts to manually review and disposition the case based on the quantitative risk scores."

### 20. Open Evaluation page
- **Action:** Navigate to the Evaluation page via the top navigation.
- **Talk Track:** "Finally, let's look at how we validate these models offline."

### 21. Show M12 External Benchmark
- **Action:** Point to the External Benchmark section.
- **Talk Track:** "We evaluated our transaction-level capabilities against a public Kaggle dataset, achieving an F1 score of 0.8199."

### 22. Explain feature/data separation
- **Action:** Emphasize the benchmark context.
- **Talk Track:** "It's important to note this benchmark tests transaction-level features only. It does not use our synthetic network data or validate our coordinated-abuse graph detection."

### 23. Show M14 robustness result
- **Action:** Point to the Robustness section.
- **Talk Track:** "We also subjected the models to adversarial robustness testing, including timing jitter and low-and-slow attacks."

### 24. Explain Low-and-Slow weakness and mitigation
- **Action:** Explain the Early Warning mitigation.
- **Talk Track:** "We found that low-and-slow attacks degrade early detection. To mitigate this, we introduced the parallel Early Warning detector, which improved detection time by over 130 minutes during a 24x slowed attack."

### 25. Conclude with limitations
- **Action:** Conclude the demo.
- **Talk Track:** "Sentinel Mesh demonstrates a robust, end-to-end architecture for risk operations. While it operates on synthetic data and has specific limitations, it proves the value of combining network intelligence, deterministic safety, and grounded AI investigation."
