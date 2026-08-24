import { useState } from 'react';
import { Shield, AlertTriangle, Activity, Network, BrainCircuit, CheckCircle, ShieldAlert, Search } from 'lucide-react';

export default function App() {
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [dossier, setDossier] = useState(null);

  // We simulate the API response you just got from FastAPI for a seamless demo
  const runInvestigation = async () => {
  setIsInvestigating(true);
  try {
    const response = await fetch('http://127.0.0.1:8001/api/v1/investigate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ entity_id: 'dev_user_83dec039' }),
});
    
    const data = await response.json();
    setDossier(data);
  } catch (error) {
    console.error("Backend connection failed, falling back to simulation", error);
    // Fallback demo data if backend isn't running yet
    setDossier({
      classification: "coordinated_abuse_ring",
      confidence: "100%",
      evidence: [
        "Associated with 20 unique accounts.",
        "Associated with 16 unique merchants."
      ],
      decision: "BLOCK",
      reason: "ML triggered high risk; AI verified coordinated cross-merchant abuse ring."
    });
  } finally {
    setIsInvestigating(false);
  }
};
  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-6 font-sans">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-800 pb-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Network className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Sentinel Mesh</h1>
            <p className="text-sm text-slate-500">Cross-Merchant Abuse Intelligence</p>
          </div>
        </div>
        <div className="flex items-center gap-4 bg-slate-900 px-4 py-2 rounded-full border border-slate-800">
          <Activity className="w-4 h-4 text-emerald-500" />
          <span className="text-sm font-medium">System B (Network) Active • FPR: 0.07%</span>
        </div>
      </header>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Transaction Feed */}
        <div className="col-span-2 space-y-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-500" />
            High-Risk Clusters Detected
          </h2>
          
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-4 font-medium">Target Entity</th>
                  <th className="p-4 font-medium">ML Risk Score</th>
                  <th className="p-4 font-medium">Graph Connections</th>
                  <th className="p-4 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                <tr className="bg-blue-900/10">
                  <td className="p-4 font-mono text-blue-400">dev_user_83dec039</td>
                  <td className="p-4">
                    <span className="bg-red-500/10 text-red-400 px-2 py-1 rounded font-semibold border border-red-500/20">0.92</span>
                  </td>
                  <td className="p-4">20 Accounts / 16 Merchants</td>
                  <td className="p-4">
                    <button 
                      onClick={runInvestigation}
                      disabled={isInvestigating || dossier}
                      className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-xs font-bold transition-all disabled:opacity-50 flex items-center gap-2"
                    >
                      <BrainCircuit className="w-4 h-4" />
                      {isInvestigating ? "Investigating..." : dossier ? "Analyzed" : "Run AI Copilot"}
                    </button>
                  </td>
                </tr>
                <tr>
                  <td className="p-4 font-mono">dev_user_c97beadf</td>
                  <td className="p-4"><span className="text-slate-400">0.14</span></td>
                  <td className="p-4">4 Accounts / 1 Merchant</td>
                  <td className="p-4"><span className="text-emerald-500 font-medium">Approved (Family Device)</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: AI Dossier */}
        <div className="col-span-1">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-6">
            <Shield className="w-5 h-5 text-blue-500" />
            AI Investigation Dossier
          </h2>
          
          {!dossier && !isInvestigating && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500 flex flex-col items-center justify-center min-h-[300px]">
              <Search className="w-8 h-8 mb-4 opacity-50" />
              <p>Awaiting manual trigger.</p>
              <p className="text-xs mt-2">Click "Run AI Copilot" to generate a grounded risk dossier.</p>
            </div>
          )}

          {isInvestigating && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 flex flex-col items-center justify-center min-h-[300px] animate-pulse">
              <BrainCircuit className="w-10 h-10 text-blue-500 mb-4 animate-bounce" />
              <p className="text-blue-400 font-medium">Querying Sentinel Mesh Graph...</p>
              <p className="text-xs text-slate-500 mt-2">Enforcing JSON Schema & Policy Engine</p>
            </div>
          )}

          {dossier && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 animate-in fade-in zoom-in duration-300">
              <div className="flex justify-between items-start border-b border-slate-800 pb-4">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Classification</p>
                  <p className="text-lg font-bold text-red-400">{dossier.classification}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Confidence</p>
                  <p className="text-lg font-mono text-white">{dossier.confidence}</p>
                </div>
              </div>
              
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-3">Deterministic Evidence</p>
                <ul className="space-y-2">
                  {dossier.evidence.map((ev, i) => (
                    <li key={i} className="flex gap-2 text-sm text-slate-300 bg-slate-950 p-2 rounded border border-slate-800">
                      <CheckCircle className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                      <span>{ev}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bg-red-950/30 border border-red-900/50 p-4 rounded-lg">
                <p className="text-xs text-red-400/70 uppercase tracking-wider font-semibold mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" /> Policy Engine Decision: {dossier.decision}
                </p>
                <p className="text-sm text-red-200">{dossier.reason}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}