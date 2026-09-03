import React, { useEffect, useState } from 'react';
import { fetchDashboardSummary, fetchCases } from '../apiClient';
import { ShieldAlert, Activity, DollarSign, Database, CheckCircle, AlertTriangle, Clock, Server, Cpu } from 'lucide-react';
import { Link } from 'react-router-dom';
import MerchantSpikePanel from '../components/MerchantSpikePanel';

function StatCard({ title, value, caption, icon: Icon, colorClass }) {
  return (
    <div className="glass-panel p-6 flex items-start gap-4 hover:bg-gray-800/40 transition-colors group">
      <div className={`p-3 rounded-xl bg-gray-800/80 border border-gray-700 group-hover:border-gray-600 transition-colors ${colorClass}`}>
        <Icon size={24} />
      </div>
      <div>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">{title}</h3>
        <p className="text-3xl font-bold text-gray-100">{value}</p>
        {caption && <p className="text-xs text-gray-500 mt-2">{caption}</p>}
      </div>
    </div>
  );
}

export default function Dashboard({ liveSimulationContext }) {
  const [summary, setSummary] = useState(null);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(false);
    try {
      const [sum, cas] = await Promise.all([
        fetchDashboardSummary(),
        fetchCases(50) // Fetch more cases to get better stats
      ]);
      setSummary(sum);
      setCases(cas);
    } catch (err) {
      console.error(err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-8 animate-pulse">
        <div className="h-12 bg-gray-800/50 rounded w-1/3"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-gray-800/50 rounded-xl"></div>)}
        </div>
        <div className="h-64 bg-gray-800/50 rounded-xl"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto mt-20">
        <div className="glass-panel p-12 text-center max-w-md mx-auto">
          <AlertTriangle className="mx-auto text-danger-500 mb-4" size={48} />
          <h2 className="text-xl font-bold text-gray-100 mb-2">Dashboard data unavailable</h2>
          <p className="text-gray-400 mb-6">We couldn't connect to the Sentinel Mesh backend.</p>
          <button onClick={loadData} className="btn btn-primary">Retry Connection</button>
        </div>
      </div>
    );
  }

  // Derived Metrics
  const earlyWarningsCount = cases.filter(c => c.triggered_signals?.includes('EARLY_WARNING')).length;

  // Detection Signal Breakdown
  const signalCounts = {
    CANDIDATE_D: 0,
    EARLY_WARNING: 0,
    MERCHANT_SPIKE: 0
  };

  let totalSignals = 0;
  cases.forEach(c => {
    if (c.triggered_signals) {
      c.triggered_signals.forEach(sig => {
        if (signalCounts[sig] !== undefined) {
          signalCounts[sig]++;
          totalSignals++;
        }
      });
    }
  });

  // Top Risk Entities
  const entityMap = {};
  cases.forEach(c => {
    const key = `${c.entity_type}-${c.entity_id}`;
    if (!entityMap[key]) {
      entityMap[key] = { type: c.entity_type, id: c.entity_id, count: 0, maxRisk: 0 };
    }
    entityMap[key].count++;
    if (c.risk_score > entityMap[key].maxRisk) {
      entityMap[key].maxRisk = c.risk_score;
    }
  });
  const topEntities = Object.values(entityMap).sort((a, b) => b.maxRisk - a.maxRisk).slice(0, 5);

  // Risk Activity (Simple Chart)
  // Group cases by day (last 7 days)
  const activityData = [];
  if (cases.length > 0) {
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split('T')[0];
      const count = cases.filter(c => c.created_at.startsWith(dateStr)).length;
      activityData.push({ date: dateStr, count });
    }
  }
  const maxActivity = Math.max(...activityData.map(d => d.count), 1);

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-12">
      {/* SECTION 1: Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
            Risk Operations Console
            <span className="badge badge-warning text-xs mt-1 border-warning-500 text-warning-400 bg-warning-900/20">LIVE SIMULATION</span>
          </h1>
          <p className="text-gray-400 mt-1">Command center for cross-merchant coordinated abuse intelligence.</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium text-success-400 bg-success-900/20 px-4 py-2 rounded-full border border-success-500/30 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
          <span className="w-2 h-2 rounded-full bg-success-500 animate-pulse"></span>
          SYSTEM OPERATIONAL
        </div>
      </div>

      {/* SECTION 2: KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Cases"
          value={summary?.total_active_cases ?? '—'}
          caption="Total open investigations"
          icon={Database}
          colorClass="text-brand-400"
        />
        <StatCard
          title="High / Critical"
          value={summary?.high_risk_cases ?? '—'}
          caption="Requires immediate review"
          icon={ShieldAlert}
          colorClass="text-danger-400"
        />
        <StatCard
          title="Early Warnings"
          value={cases.length > 0 ? earlyWarningsCount : '—'}
          caption="Pre-fraud indicators detected"
          icon={Clock}
          colorClass="text-warning-400"
        />
        <StatCard
          title="Estimated Exposure"
          value={summary?.estimated_exposure !== undefined ? `$${summary.estimated_exposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
          caption="Potential fraud loss prevented"
          icon={DollarSign}
          colorClass="text-emerald-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SECTION 3: Risk Activity */}
        <div className="glass-panel p-6 lg:col-span-2 flex flex-col">
          <h2 className="text-lg font-semibold text-gray-100 mb-1">Risk Activity</h2>
          <p className="text-xs text-gray-400 mb-6">Recent risk-case activity over the last 7 days</p>

          <div className="flex-1 flex items-end gap-2 h-40 mt-auto">
            {activityData.length > 0 ? (
              activityData.map((d, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                  <div className="w-full bg-gray-800/50 rounded-t-md relative flex items-end justify-center h-full">
                    <div
                      className="w-full bg-brand-500/80 rounded-t-md transition-all duration-500 group-hover:bg-brand-400"
                      style={{ height: `${(d.count / maxActivity) * 100}%`, minHeight: d.count > 0 ? '4px' : '0' }}
                    ></div>
                    {/* Tooltip */}
                    <div className="absolute -top-8 bg-gray-800 text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10 border border-gray-700">
                      {d.count} cases
                    </div>
                  </div>
                  <span className="text-[10px] text-gray-500">{new Date(d.date).toLocaleDateString(undefined, { weekday: 'short' })}</span>
                </div>
              ))
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-500 text-sm">
                No recent activity data available.
              </div>
            )}
          </div>
        </div>

        {/* SECTION 4: Detection Signal Breakdown */}
        <div className="glass-panel p-6 flex flex-col">
          <h2 className="text-lg font-semibold text-gray-100 mb-1">Detection Signals</h2>
          <p className="text-xs text-gray-400 mb-6">Distribution of triggered risk signals</p>

          {totalSignals > 0 ? (
            <div className="space-y-5 flex-1">
              {[
                { key: 'CANDIDATE_D', label: 'Candidate D', color: 'bg-brand-500' },
                { key: 'EARLY_WARNING', label: 'Early Warning', color: 'bg-warning-500' },
                { key: 'MERCHANT_SPIKE', label: 'Merchant Spike', color: 'bg-danger-500' }
              ].map(sig => {
                const count = signalCounts[sig.key];
                const pct = Math.round((count / totalSignals) * 100) || 0;
                return (
                  <div key={sig.key}>
                    <div className="flex justify-between text-sm mb-1.5">
                      <span className="text-gray-300 font-medium">{sig.label}</span>
                      <span className="text-gray-400">{count} <span className="text-gray-500 text-xs">({pct}%)</span></span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                      <div className={`h-2 rounded-full ${sig.color}`} style={{ width: `${pct}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-center p-4 border border-dashed border-gray-700 rounded-lg">
              <p className="text-sm text-gray-500">Signal distribution becomes available as cases are enriched.</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SECTION 5: Top Risk Entities */}
        <div className="glass-panel overflow-hidden lg:col-span-1 flex flex-col">
          <div className="px-6 py-4 border-b border-gray-700/50 bg-gray-800/30">
            <h2 className="text-lg font-semibold text-gray-100">Top Risk Entities</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {topEntities.length > 0 ? (
              <div className="space-y-3">
                {topEntities.map((ent, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/40 border border-gray-700/50 hover:bg-gray-800/60 transition-colors">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[9px] font-bold uppercase tracking-wider bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">{ent.type}</span>
                        <span className="text-sm font-mono text-gray-200 truncate max-w-[120px]">{ent.id}</span>
                      </div>
                      <div className="text-xs text-gray-500">{ent.count} active cases</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-500 mb-1">Max Risk</div>
                      <span className={`badge ${ent.maxRisk >= 0.8 ? 'badge-danger' : ent.maxRisk >= 0.5 ? 'badge-warning' : 'badge-neutral'}`}>
                        {ent.maxRisk.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                No entities found.
              </div>
            )}
          </div>
        </div>

        {/* SECTION 6: Recent Cases */}
        <div className="glass-panel overflow-hidden lg:col-span-2 flex flex-col">
          <div className="px-6 py-4 border-b border-gray-700/50 bg-gray-800/30 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-100">Recent Cases</h2>
            <span className="text-xs text-gray-500">Showing latest {cases.slice(0, 10).length}</span>
          </div>
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800/40 text-gray-400 uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-6 py-3 font-semibold">Case ID</th>
                  <th className="px-6 py-3 font-semibold">Entity</th>
                  <th className="px-6 py-3 font-semibold">Risk</th>
                  <th className="px-6 py-3 font-semibold">Status</th>
                  <th className="px-6 py-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {cases.slice(0, 10).map((c) => (
                  <tr key={c.case_id} className="hover:bg-gray-700/20 transition-colors group">
                    <td className="px-6 py-4 font-mono text-xs text-gray-400 group-hover:text-gray-300">{c.case_id}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-bold uppercase tracking-wider bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded border border-gray-700">{c.entity_type || 'TRANSACTION'}</span>
                        <span className="font-mono text-xs text-gray-300 truncate max-w-[150px]">{c.entity_id || c.transaction_id}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${c.risk_level === 'CRITICAL' || c.risk_level === 'HIGH' ? 'bg-danger-500' : c.risk_level === 'MEDIUM' ? 'bg-warning-500' : 'bg-gray-500'}`}></span>
                        <span className="font-mono">{c.risk_score.toFixed(2)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {c.status === 'CLOSED' ? (
                        <span className="inline-flex items-center gap-1.5 text-gray-500 text-xs font-medium">
                          <CheckCircle size={12} /> Closed
                        </span>
                      ) : c.investigation_status === 'UNINVESTIGATED' ? (
                        <span className="inline-flex items-center gap-1.5 text-warning-400 text-xs font-medium">
                          <Clock size={12} /> Pending
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-brand-400 text-xs font-medium">
                          <Activity size={12} /> Investigated
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/cases/${c.case_id}${c.is_ai_failure ? '?scenario=AI_FAILURE' : ''}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-brand-500/10 text-brand-400 hover:bg-brand-500/20 hover:text-brand-300 transition-colors text-xs font-semibold"
                      >
                        View Details &rarr;
                      </Link>
                    </td>
                  </tr>
                ))}
                {cases.length === 0 && (
                  <tr>
                    <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                      <div className="flex flex-col items-center gap-2">
                        <Database size={24} className="text-gray-600" />
                        <p>No active risk cases. Try running a simulation.</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* SECTION 7: Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <MerchantSpikePanel liveSimulationContext={liveSimulationContext} />
        </div>

        <div className="glass-panel p-6 flex flex-col">
          <div className="flex items-center gap-2 mb-6">
            <Server className="text-gray-400" size={20} />
            <h2 className="text-lg font-semibold text-gray-100">Detection Stack</h2>
          </div>

          <div className="space-y-4 flex-1">
            {[
              { name: 'Candidate D', status: 'ONLINE', type: 'model' },
              { name: 'Early Warning', status: 'ONLINE', type: 'detector' },
              { name: 'Merchant Spike', status: 'ONLINE', type: 'detector' },
              { name: 'Policy Engine', status: 'ONLINE', type: 'system' },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm text-gray-300">{item.name}</span>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-success-500"></span>
                  <span className="text-xs font-mono text-success-400">{item.status}</span>
                </div>
              </div>
            ))}

            <div className="pt-4 mt-4 border-t border-gray-700/50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Cpu className="text-brand-400" size={16} />
                  <span className="text-sm font-medium text-gray-200">AI Investigator</span>
                </div>
                <div className="flex items-center gap-2 bg-brand-900/20 px-2 py-1 rounded border border-brand-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-500"></span>
                  <span className="text-xs font-mono text-brand-400">READY</span>
                </div>
              </div>
              <p className="text-[10px] text-gray-500 leading-relaxed">
                AI is investigation-assistive; deterministic policy remains authoritative.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
