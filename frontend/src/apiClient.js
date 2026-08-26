const API_BASE = 'http://127.0.0.1:8000/api/v1';

export const fetchDashboardSummary = async () => {
  const res = await fetch(`${API_BASE}/dashboard/summary`);
  if (!res.ok) throw new Error('Failed to fetch summary');
  return res.json();
};

export const fetchCases = async (limit = 50) => {
  const res = await fetch(`${API_BASE}/cases?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch cases');
  return res.json();
};

export const fetchCaseDetail = async (caseId) => {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!res.ok) throw new Error('Failed to fetch case detail');
  return res.json();
};

export const investigateCase = async (caseId, simulateAiFailure = false) => {
  const url = `${API_BASE}/cases/${caseId}/investigate${simulateAiFailure ? '?simulate_ai_failure=true' : ''}`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) throw new Error('Investigation failed');
  return res.json();
};

export const fetchEvaluation = async () => {
  const res = await fetch(`${API_BASE}/evaluation`);
  if (!res.ok) throw new Error('Failed to fetch evaluation');
  return res.json();
};

export const runSimulationStep = async (scenario) => {
  const res = await fetch(`${API_BASE}/simulation/step`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario })
  });
  if (!res.ok) throw new Error('Simulation step failed');
  return res.json();
};
