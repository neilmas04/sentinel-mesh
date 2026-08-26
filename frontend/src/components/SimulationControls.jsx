import React, { useState } from 'react';
import { runSimulationStep } from '../apiClient';
import { Play, Activity, AlertTriangle, AlertOctagon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function SimulationControls() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSimulate = async (scenario) => {
    setLoading(true);
    try {
      const result = await runSimulationStep(scenario);
      if (result.case_id) {
        navigate(`/cases/${result.case_id}?scenario=${scenario}`);
      } else {
        alert('Simulation complete: low-risk transaction; no Risk Case created.');
      }
    } catch (err) {
      console.error(err);
      alert('Simulation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Simulation Mode</h3>
      <button
        onClick={() => handleSimulate('NORMAL')}
        disabled={loading}
        className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded border border-gray-700 transition flex items-center gap-2 text-sm"
      >
        <Play size={14} className="text-success-500" /> Normal Traffic
      </button>
      <button
        onClick={() => handleSimulate('COORDINATED_ACTIVITY')}
        disabled={loading}
        className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded border border-gray-700 transition flex items-center gap-2 text-sm"
      >
        <Activity size={14} className="text-warning-500" /> Emerging Cluster
      </button>
      <button
        onClick={() => handleSimulate('AI_FAILURE')}
        disabled={loading}
        className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded border border-gray-700 transition flex items-center gap-2 text-sm"
      >
        <AlertTriangle size={14} className="text-danger-500" /> AI Failure
      </button>
    </div>
  );
}
