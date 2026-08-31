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

export const fetchCaseSignals = async (caseId) => {
  const res = await fetch(`${API_BASE}/cases/${caseId}/signals`);
  if (!res.ok) throw new Error('Failed to fetch case signals');
  return res.json();
};

export const fetchCaseAuditLog = async (caseId) => {
  const res = await fetch(`${API_BASE}/cases/${caseId}/audit`);
  if (!res.ok) throw new Error('Failed to fetch case audit log');
  return res.json();
};

export const setCaseDisposition = async (caseId, disposition, analystNotes, analystId) => {
  const res = await fetch(`${API_BASE}/cases/${caseId}/disposition`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ disposition, analyst_notes: analystNotes, analyst_id: analystId })
  });
  if (!res.ok) throw new Error('Failed to set disposition');
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

export const fetchMerchantSpikes = async (merchantId = null, currentTime = null, liveTxId = null, liveIsFlagged = null) => {
  let url = `${API_BASE}/merchant-spikes`;
  const params = new URLSearchParams();
  if (merchantId) params.append('merchant_id', merchantId);
  if (currentTime) params.append('current_time', currentTime);
  if (liveTxId) params.append('live_tx_id', liveTxId);
  if (liveIsFlagged !== null) params.append('live_is_flagged', liveIsFlagged);

  const queryString = params.toString();
  if (queryString) {
    url += `?${queryString}`;
  }

  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch merchant spikes');
  return res.json();
};
