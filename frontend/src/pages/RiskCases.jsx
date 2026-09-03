import React, { useEffect, useState } from 'react';
import { fetchCases } from '../apiClient';
import { ShieldAlert, Search, Filter, CheckCircle, Clock, Activity, AlertTriangle, Database } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function RiskCases() {
    const [cases, setCases] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    // Filters
    const [searchTerm, setSearchTerm] = useState('');
    const [severityFilter, setSeverityFilter] = useState('All');
    const [statusFilter, setStatusFilter] = useState('All');

    const loadData = async () => {
        setLoading(true);
        setError(false);
        try {
            const data = await fetchCases(50);
            setCases(data);
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

    if (error) {
        return (
            <div className="max-w-6xl mx-auto mt-20">
                <div className="glass-panel p-12 text-center max-w-md mx-auto">
                    <AlertTriangle className="mx-auto text-danger-500 mb-4" size={48} />
                    <h2 className="text-xl font-bold text-gray-100 mb-2">Risk case data unavailable</h2>
                    <p className="text-gray-400 mb-6">We couldn't connect to the Sentinel Mesh backend.</p>
                    <button onClick={loadData} className="btn btn-primary">Retry Connection</button>
                </div>
            </div>
        );
    }

    // Filter Logic
    const filteredCases = cases.filter(c => {
        const matchesSearch = searchTerm === '' ||
            c.case_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (c.entity_id || c.transaction_id || '').toLowerCase().includes(searchTerm.toLowerCase());

        const matchesSeverity = severityFilter === 'All' || c.risk_level === severityFilter.toUpperCase();

        let matchesStatus = true;
        if (statusFilter === 'Uninvestigated') {
            matchesStatus = c.investigation_status === 'UNINVESTIGATED' && c.status !== 'CLOSED';
        } else if (statusFilter === 'Investigated') {
            matchesStatus = c.investigation_status !== 'UNINVESTIGATED' && c.status !== 'CLOSED';
        } else if (statusFilter === 'Closed') {
            matchesStatus = c.status === 'CLOSED';
        }

        return matchesSearch && matchesSeverity && matchesStatus;
    });

    const formatSignal = (sig) => {
        const map = {
            'CANDIDATE_D': 'Candidate D',
            'EARLY_WARNING': 'Early Warning',
            'MERCHANT_SPIKE': 'Merchant Spike'
        };
        return map[sig] || sig;
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6 pb-12">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
                        Risk Case Queue
                    </h1>
                    <p className="text-gray-400 mt-1">Investigate, review, and disposition detected risk cases.</p>
                </div>
                {!loading && (
                    <div className="flex items-center gap-2 text-xs font-medium text-gray-300 bg-gray-800/50 px-4 py-2 rounded-full border border-gray-700">
                        Showing {filteredCases.length} cases
                    </div>
                )}
            </div>

            {/* Filters */}
            <div className="glass-panel p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                    <input
                        type="text"
                        placeholder="Search Case ID or Entity ID..."
                        className="w-full bg-gray-900 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500 transition-colors"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className="flex items-center gap-4 w-full md:w-auto">
                    <div className="flex items-center gap-2">
                        <Filter size={14} className="text-gray-500" />
                        <select
                            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-brand-500"
                            value={severityFilter}
                            onChange={(e) => setSeverityFilter(e.target.value)}
                        >
                            <option value="All">All Severities</option>
                            <option value="Critical">Critical</option>
                            <option value="High">High</option>
                            <option value="Medium">Medium</option>
                            <option value="Low">Low</option>
                        </select>
                    </div>
                    <div className="flex items-center gap-2">
                        <select
                            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-brand-500"
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                        >
                            <option value="All">All Statuses</option>
                            <option value="Uninvestigated">Uninvestigated</option>
                            <option value="Investigated">Investigated</option>
                            <option value="Closed">Closed</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Table */}
            <div className="glass-panel overflow-hidden flex flex-col">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-gray-300">
                        <thead className="bg-gray-800/40 text-gray-400 uppercase text-[10px] tracking-wider">
                            <tr>
                                <th className="px-6 py-3 font-semibold">Case ID</th>
                                <th className="px-6 py-3 font-semibold">Entity</th>
                                <th className="px-6 py-3 font-semibold">Risk Score</th>
                                <th className="px-6 py-3 font-semibold">Severity</th>
                                <th className="px-6 py-3 font-semibold">Signal(s)</th>
                                <th className="px-6 py-3 font-semibold">Investigation Status</th>
                                <th className="px-6 py-3 font-semibold">Disposition</th>
                                <th className="px-6 py-3 font-semibold text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/50">
                            {loading ? (
                                // Skeleton Rows
                                Array.from({ length: 5 }).map((_, i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td className="px-6 py-4"><div className="h-4 bg-gray-800 rounded w-24"></div></td>
                                        <td className="px-6 py-4"><div className="h-4 bg-gray-800 rounded w-32"></div></td>
                                        <td className="px-6 py-4"><div className="h-4 bg-gray-800 rounded w-12"></div></td>
                                        <td className="px-6 py-4"><div className="h-4 bg-gray-800 rounded w-16"></div></td>
                                        <td className="px-6 py-4"><div className="h-4 bg-gray-800 rounded w-20"></div></td>
                                        <td className="px-6 py-4"><div className="h-4 bg-gray-800 rounded w-24"></div></td>
                                        <td className="px-6 py-4"><div className="h-4 bg-gray-800 rounded w-20"></div></td>
                                        <td className="px-6 py-4 text-right"><div className="h-6 bg-gray-800 rounded w-24 ml-auto"></div></td>
                                    </tr>
                                ))
                            ) : filteredCases.length > 0 ? (
                                filteredCases.map((c) => (
                                    <tr key={c.case_id} className="hover:bg-gray-700/20 transition-colors group">
                                        <td className="px-6 py-4 font-mono text-xs text-gray-400 group-hover:text-gray-300">{c.case_id}</td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[9px] font-bold uppercase tracking-wider bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded border border-gray-700">{c.entity_type || 'TRANSACTION'}</span>
                                                <span className="font-mono text-xs text-gray-300 truncate max-w-[120px]">{c.entity_id || c.transaction_id}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 font-mono">{c.risk_score.toFixed(4)}</td>
                                        <td className="px-6 py-4">
                                            <span className={`badge ${c.risk_level === 'CRITICAL' || c.risk_level === 'HIGH' ? 'badge-danger' : c.risk_level === 'MEDIUM' ? 'badge-warning' : 'badge-neutral'}`}>
                                                {c.risk_level}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            {c.triggered_signals && c.triggered_signals.length > 0 ? (
                                                <div className="flex flex-wrap gap-1">
                                                    {c.triggered_signals.map((sig, idx) => (
                                                        <span key={idx} className="text-[10px] bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded border border-gray-700">
                                                            {formatSignal(sig)}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <span className="text-gray-500">—</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            {c.investigation_status === 'UNINVESTIGATED' ? (
                                                <span className="inline-flex items-center gap-1.5 text-warning-400 text-xs font-medium">
                                                    <Clock size={12} /> Pending
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1.5 text-brand-400 text-xs font-medium">
                                                    <Activity size={12} /> Investigated
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            {c.disposition ? (
                                                <span className="inline-flex items-center gap-1.5 text-gray-300 text-xs font-medium">
                                                    <CheckCircle size={12} className="text-success-500" /> {c.disposition}
                                                </span>
                                            ) : (
                                                <span className="text-gray-500">—</span>
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
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="8" className="px-6 py-16 text-center text-gray-500">
                                        <div className="flex flex-col items-center gap-3">
                                            <Database size={32} className="text-gray-600" />
                                            <div>
                                                <p className="text-gray-300 font-medium mb-1">No risk cases yet</p>
                                                <p className="text-sm">Run a simulation from the sidebar to generate investigation cases.</p>
                                            </div>
                                        </div>
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
