import React, { useEffect, useState } from 'react';
import { fetchEvaluation } from '../apiClient';
import { BarChart3, Info } from 'lucide-react';

export default function Evaluation() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchEvaluation();
        setMetrics(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="animate-pulse">Loading evaluation metrics...</div>;
  if (!metrics || metrics.error) {
    return (
      <div className="text-danger-500 glass-card p-6">
        <h2 className="text-xl font-bold mb-2">Evaluation Artifacts Missing</h2>
        <p>{metrics?.error || 'Failed to load evaluation metrics.'}</p>
      </div>
    );
  }

  // Helper to format a metric
  const formatMetric = (val) => {
    if (val === undefined || val === null) return 'N/A';
    if (typeof val === 'number') {
      // If it's a cost, format as currency, else 4 decimals max
      if (val > 100) return `$${val.toFixed(2)}`;
      return val.toFixed(4);
    }
    return val;
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-20">
      <div>
        <h1 className="text-3xl font-bold text-gray-100 flex items-center gap-2">
          <BarChart3 className="text-brand-500" /> Synthetic Held-Out Evaluation
        </h1>
        <p className="text-gray-400 mt-2">
          Historical benchmark metrics for M02, M03, M04, and Candidate D models.
        </p>
      </div>

      <div className="bg-brand-900/20 border border-brand-500/30 rounded-lg p-4 flex gap-3 text-sm text-gray-300">
        <Info size={18} className="text-brand-500 flex-shrink-0" />
        <div>
          <strong className="text-brand-400">Important:</strong> These results reflect 
          <strong> synthetic benchmarks</strong> and <strong>synthetic economic assumptions</strong>.
          They do not represent live production metrics.
        </div>
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700 bg-gray-800/50">
          <h2 className="text-lg font-semibold text-gray-100">Model Ablation Results</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="bg-gray-800/50 text-gray-400 uppercase text-xs">
              <tr>
                <th className="px-6 py-3 font-medium">Model</th>
                <th className="px-6 py-3 font-medium">Precision</th>
                <th className="px-6 py-3 font-medium">Recall</th>
                <th className="px-6 py-3 font-medium">F1 Score</th>
                <th className="px-6 py-3 font-medium">FPR</th>
                <th className="px-6 py-3 font-medium">Expected Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700 font-mono text-xs">
              {[
                { key: 'System A (Local Only)', label: 'M02 Baseline' },
                { key: 'System B (All Network)', label: 'M03 Network' },
                { key: 'System C (B* + All Temporal)', label: 'M04 Temporal' }
              ].map(sys => {
                const row = metrics.m04?.ablations?.[sys.key]?.metrics;
                if (!row) return null;
                return (
                  <tr key={sys.key} className="hover:bg-gray-800/30">
                    <td className="px-6 py-4 text-gray-200">{sys.label}</td>
                    <td className="px-6 py-4">{formatMetric(row.precision)}</td>
                    <td className="px-6 py-4">{formatMetric(row.recall)}</td>
                    <td className="px-6 py-4 font-bold text-brand-400">{formatMetric(row.f1)}</td>
                    <td className="px-6 py-4">{formatMetric(row.fpr)}</td>
                    <td className="px-6 py-4 text-warning-400">{formatMetric(row.expected_cost)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {(() => {
        const cand = metrics.m04?.ablations?.['System C (B* + All Temporal)']?.metrics;
        if (!cand) return null;
        return (
          <div className="glass-panel p-6 border-brand-500/30 relative overflow-hidden mt-8">
            <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/10 rounded-full blur-3xl transform translate-x-10 -translate-y-10"></div>
            
            <h2 className="text-xl font-bold text-gray-100 mb-4">Candidate D (Operating Point)</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-xs text-gray-400 uppercase">Detection Coverage</p>
                <p className="text-xl font-bold text-gray-100">{formatMetric(cand.coverage)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase">Median TTD</p>
                <p className="text-xl font-bold text-gray-100">{formatMetric(cand.median_ttd_mins / (24 * 60))} days</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase">Recall</p>
                <p className="text-xl font-bold text-brand-400">{formatMetric(cand.recall)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase">Precision</p>
                <p className="text-xl font-bold text-brand-400">{formatMetric(cand.precision)}</p>
              </div>
            </div>
          </div>
        );
      })()}

      {metrics.m04_r && (
        <div className="glass-panel overflow-hidden mt-8">
          <div className="px-6 py-4 border-b border-gray-700 bg-gray-800/50">
            <h2 className="text-lg font-semibold text-gray-100">M04-R Robustness Test (Noise + Temporal Shift)</h2>
          </div>
          <div className="p-6 grid grid-cols-2 gap-6">
             <div>
               <p className="text-sm font-medium text-gray-300">Baseline F1</p>
               <p className="text-lg font-mono text-gray-400">{formatMetric(metrics.m04_r.baseline_f1)}</p>
             </div>
             <div>
               <p className="text-sm font-medium text-gray-300">Shifted F1</p>
               <p className="text-lg font-mono text-warning-500">{formatMetric(metrics.m04_r.shifted_f1)}</p>
             </div>
             <div className="col-span-2">
               <p className="text-sm font-medium text-gray-300">Drop Ratio</p>
               <p className="text-lg font-mono text-danger-400">
                 {((metrics.m04_r.baseline_f1 - metrics.m04_r.shifted_f1) / metrics.m04_r.baseline_f1 * 100).toFixed(2)}%
               </p>
               <p className="text-xs text-gray-500 mt-2">
                 Shows the model's resistance to data drift and intentional obfuscation of temporal signals.
               </p>
             </div>
          </div>
        </div>
      )}
    </div>
  );
}
