import React, { useEffect, useState } from 'react';
import { fetchDashboardSummary, fetchCases } from '../apiClient';
import { ShieldAlert, Activity, DollarSign, Database } from 'lucide-react';
import { Link } from 'react-router-dom';
import MerchantSpikePanel from '../components/MerchantSpikePanel';

function StatCard({ title, value, icon: Icon, colorClass }) {
  return (
    <div className="glass-panel p-6 flex items-center gap-4">
      <div className={`p-4 rounded-full bg-gray-800 ${colorClass}`}>
        <Icon size={24} />
      </div>
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">{title}</h3>
        <p className="text-2xl font-bold text-gray-100 mt-1">{value}</p>
      </div>
    </div>
  );
}

export default function Dashboard({ liveSimulationContext }) {
  const [summary, setSummary] = useState(null);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [sum, cas] = await Promise.all([
          fetchDashboardSummary(),
          fetchCases(10)
        ]);
        setSummary(sum);
        setCases(cas);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="text-gray-400 animate-pulse">Loading dashboard...</div>;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
          Risk Operations Console <span className="badge badge-warning text-xs mt-1 border-warning-500 text-warning-400 bg-warning-900/20">LIVE SIMULATION</span>
        </h1>
        <p className="text-gray-400 mt-1">Live monitoring and investigation queue for simulated data.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard title="Active Cases" value={summary?.total_active_cases || 0} icon={Database} colorClass="text-brand-500" />
        <StatCard title="High Risk" value={summary?.high_risk_cases || 0} icon={ShieldAlert} colorClass="text-danger-500" />
        <StatCard title="Investigated" value={summary?.investigated_cases || 0} icon={Activity} colorClass="text-success-500" />
        <StatCard title="Exposure" value={`$${(summary?.estimated_exposure || 0).toFixed(2)}`} icon={DollarSign} colorClass="text-warning-500" />
      </div>

      <MerchantSpikePanel liveSimulationContext={liveSimulationContext} />

      <div className="glass-panel overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700 bg-gray-800/50">
          <h2 className="text-lg font-semibold text-gray-100">Recent Cases</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="bg-gray-800/50 text-gray-400 uppercase text-xs">
              <tr>
                <th className="px-6 py-3 font-medium">Case ID</th>
                <th className="px-6 py-3 font-medium">Entity</th>
                <th className="px-6 py-3 font-medium">Risk Score</th>
                <th className="px-6 py-3 font-medium">Risk Level</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {cases.map((c) => (
                <tr key={c.case_id} className="hover:bg-gray-800/30 transition">
                  <td className="px-6 py-4 font-mono text-xs">{c.case_id}</td>
                  <td className="px-6 py-4 font-mono text-xs text-gray-500">
                    <span className="text-[10px] uppercase bg-gray-700 px-1 rounded mr-1">{c.entity_type || 'TRANSACTION'}</span>
                    {c.entity_id || c.transaction_id}
                  </td>
                  <td className="px-6 py-4 font-mono">{c.risk_score.toFixed(4)}</td>
                  <td className="px-6 py-4">
                    <span className={`badge ${c.risk_level === 'HIGH' ? 'badge-danger' : c.risk_level === 'MEDIUM' ? 'badge-warning' : 'badge-neutral'}`}>
                      {c.risk_level}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {c.status === 'CLOSED' ? (
                      <span className="text-gray-500">Closed ({c.disposition})</span>
                    ) : c.investigation_status === 'UNINVESTIGATED' ? (
                      <span className="text-gray-500">Uninvestigated</span>
                    ) : (
                      <span className="text-brand-500">Investigated</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <Link to={`/cases/${c.case_id}${c.is_ai_failure ? '?scenario=AI_FAILURE' : ''}`} className="text-brand-500 hover:text-brand-400 font-medium">View &rarr;</Link>
                  </td>
                </tr>
              ))}
              {cases.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                    No active risk cases. Try running a simulation.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
