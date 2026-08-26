import React, { useEffect, useState } from 'react';
import { fetchMerchantSpikes } from '../apiClient';
import { TrendingUp, AlertTriangle, ShieldCheck, AlertOctagon } from 'lucide-react';

export default function MerchantSpikePanel({ liveSimulationContext }) {
    const [spikes, setSpikes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadSpikes() {
            setLoading(true);
            setError(null);
            try {
                let data;
                if (liveSimulationContext) {
                    data = await fetchMerchantSpikes(
                        liveSimulationContext.merchant_id,
                        liveSimulationContext.as_of_timestamp,
                        liveSimulationContext.live_tx_id,
                        liveSimulationContext.live_is_flagged
                    );
                } else {
                    data = await fetchMerchantSpikes();
                }
                setSpikes(data);
            } catch (err) {
                console.error(err);
                setError('Failed to load merchant spikes.');
            } finally {
                setLoading(false);
            }
        }
        loadSpikes();
    }, [liveSimulationContext]);

    if (loading) {
        return <div className="glass-panel p-6 text-gray-400 animate-pulse">Loading merchant spike data...</div>;
    }

    if (error) {
        return <div className="glass-panel p-6 text-danger-500">{error}</div>;
    }

    if (spikes.length === 0) {
        return <div className="glass-panel p-6 text-gray-500">No merchant spike data available.</div>;
    }

    const getSeverityBadge = (severity) => {
        switch (severity) {
            case 'CRITICAL':
                return <span className="badge badge-danger flex items-center gap-1"><AlertOctagon size={12} /> CRITICAL</span>;
            case 'HIGH':
                return <span className="badge badge-warning flex items-center gap-1"><AlertTriangle size={12} /> HIGH</span>;
            case 'ELEVATED':
                return <span className="badge text-warning-400 border-warning-500 bg-warning-900/20 flex items-center gap-1"><TrendingUp size={12} /> ELEVATED</span>;
            case 'NORMAL':
            default:
                return <span className="badge badge-neutral flex items-center gap-1"><ShieldCheck size={12} /> NORMAL</span>;
        }
    };

    return (
        <div className="glass-panel overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-700 bg-gray-800/50 flex justify-between items-center">
                <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                    <TrendingUp size={18} className="text-brand-500" />
                    {liveSimulationContext ? 'Live Simulation Merchant Spike' : 'Historical Merchant Risk Spikes'}
                </h2>
                <span className="text-xs text-gray-500">
                    {liveSimulationContext ? 'Live Simulation State' : 'Historical M01 State'} • Last updated: {new Date(spikes[0]?.timestamp).toLocaleString()}
                </span>
            </div>
            <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left text-sm text-gray-300">
                    <thead className="bg-gray-800/50 text-gray-400 uppercase text-xs sticky top-0">
                        <tr>
                            <th className="px-6 py-3 font-medium">Merchant ID</th>
                            <th className="px-6 py-3 font-medium">Severity</th>
                            <th className="px-6 py-3 font-medium">Flagged / Total</th>
                            <th className="px-6 py-3 font-medium">Rate</th>
                            <th className="px-6 py-3 font-medium">Baseline (μ ± σ)</th>
                            <th className="px-6 py-3 font-medium">Multiplier</th>
                            <th className="px-6 py-3 font-medium">Spike Score</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {spikes.map((s) => (
                            <tr key={s.merchant_id} className="hover:bg-gray-800/30 transition">
                                <td className="px-6 py-4 font-mono text-xs">{s.merchant_id}</td>
                                <td className="px-6 py-4">{getSeverityBadge(s.severity)}</td>
                                <td className="px-6 py-4">{s.flagged_transactions} / {s.total_transactions}</td>
                                <td className="px-6 py-4 font-mono">{(s.flagged_rate * 100).toFixed(1)}%</td>
                                <td className="px-6 py-4 font-mono text-gray-400">
                                    {s.baseline_insufficient ? (
                                        <span className="text-gray-500 italic">Insufficient Data</span>
                                    ) : (
                                        `${(s.baseline_mean * 100).toFixed(1)}% ± ${(s.baseline_std * 100).toFixed(1)}%`
                                    )}
                                </td>
                                <td className="px-6 py-4 font-mono">
                                    {s.rate_multiplier !== null ? `${s.rate_multiplier.toFixed(2)}x` : '-'}
                                </td>
                                <td className="px-6 py-4 font-mono">
                                    {s.spike_score !== null ? s.spike_score.toFixed(2) : '-'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
