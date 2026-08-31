import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchCaseDetail, investigateCase, fetchCaseSignals, fetchCaseAuditLog, setCaseDisposition } from '../apiClient';
import { AlertCircle, FileText, CheckCircle2, ShieldAlert, Cpu, Activity, List, UserCheck } from 'lucide-react';
import NetworkGraph from '../components/NetworkGraph';

export default function CaseDetail() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [signals, setSignals] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [dispositionForm, setDispositionForm] = useState({ disposition: 'CONFIRMED_ABUSE', notes: '' });
  const [submittingDisposition, setSubmittingDisposition] = useState(false);

  const loadData = async () => {
    try {
      const [data, sigs, audit] = await Promise.all([
        fetchCaseDetail(caseId),
        fetchCaseSignals(caseId),
        fetchCaseAuditLog(caseId)
      ]);
      setCaseData(data);
      setSignals(sigs);
      setAuditLog(audit);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId]);

  const handleInvestigate = async () => {
    setInvestigating(true);
    try {
      const isAiFailure = new URLSearchParams(window.location.search).get('scenario') === 'AI_FAILURE';
      await investigateCase(caseId, isAiFailure);
      await loadData(); // Reload everything
    } catch (err) {
      console.error(err);
      alert('Investigation failed.');
    } finally {
      setInvestigating(false);
    }
  };

  const handleDispositionSubmit = async (e) => {
    e.preventDefault();
    setSubmittingDisposition(true);
    try {
      await setCaseDisposition(caseId, dispositionForm.disposition, dispositionForm.notes, "ANALYST-01");
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to submit disposition.');
    } finally {
      setSubmittingDisposition(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse">Loading case details...</div>;
  }

  if (!caseData) {
    return <div className="text-danger-500">Case not found.</div>;
  }

  const {
    risk_score,
    risk_level,
    model_version,
    created_at,
    investigation_status,
    status,
    entity_type,
    entity_id,
    disposition,
    analyst_notes,
    evidence,
    evidence_bundle, // from get_case
    ai_dossier,
    policy_decision,
    tool_trace,
    tools_used // from get_case
  } = caseData;

  const actualEvidence = evidence || evidence_bundle;
  const actualTools = tool_trace || tools_used;

  const renderClaim = (f, i) => {
    if (typeof f === 'string') {
      return <li key={i} className="mb-2 list-disc ml-4 text-sm text-gray-300">{f}</li>;
    }

    const statusStyle = {
      SUPPORTED: 'text-success-400 bg-success-900/10 border-success-500/30',
      UNSUPPORTED: 'text-danger-400 bg-danger-900/10 border-danger-500/30',
      UNVERIFIABLE: 'text-warning-400 bg-warning-900/10 border-warning-500/30'
    };

    const containerClass = statusStyle[f.grounding_status] || 'text-gray-400 bg-gray-800/50 border-gray-700/50';

    return (
      <li key={i} className={`p-3 rounded border mb-3 list-none ${containerClass}`}>
        <div className="flex justify-between items-start mb-2">
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-80">{f.type || 'CLAIM'}</span>
          <div className="flex gap-2">
            {f.evidence_ids?.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-900/50 opacity-80">
                Ev: {f.evidence_ids.join(', ')}
              </span>
            )}
            {f.grounding_status && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-900/50 font-semibold">
                {f.grounding_status}
              </span>
            )}
          </div>
        </div>
        <p className="text-sm text-gray-200 mb-2">{f.claim}</p>
        {f.grounding_reason && (
          <p className="text-[11px] opacity-80 border-t border-current pt-2 mt-2">
            {f.grounding_reason}
          </p>
        )}
      </li>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-gray-100 font-mono">{caseId}</h1>
          <p className="text-gray-400 text-sm mt-1">Generated: {new Date(created_at || new Date()).toLocaleString()}</p>
        </div>
        {status === 'CLOSED' ? (
          <span className="badge badge-neutral px-3 py-1 flex items-center gap-2">
            <CheckCircle2 size={14} className="text-gray-400" /> Closed ({disposition})
          </span>
        ) : investigation_status === 'UNINVESTIGATED' ? (
          <button
            onClick={handleInvestigate}
            disabled={investigating}
            className="btn btn-primary"
          >
            {investigating ? 'Investigating...' : 'Start Investigation'}
          </button>
        ) : (
          <span className="badge badge-neutral px-3 py-1 flex items-center gap-2">
            <CheckCircle2 size={14} className="text-success-500" /> Investigated
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-5">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Risk Profile</h3>
          <div className="space-y-4">
            <div>
              <p className="text-xs text-gray-400">Entity</p>
              <p className="text-lg font-mono text-gray-200 mt-1">
                <span className="text-[10px] uppercase bg-gray-700 px-1 rounded mr-1">{entity_type || 'TRANSACTION'}</span>
                {entity_id}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-400">Risk Level</p>
                <p className={`text-xl font-bold mt-1 ${risk_level === 'HIGH' ? 'text-danger-500' : 'text-warning-500'}`}>{risk_level}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Risk Score</p>
                <p className="text-lg font-mono text-gray-200 mt-1">{risk_score?.toFixed(4)}</p>
              </div>
            </div>
            {model_version && (
              <div className="pt-2 border-t border-gray-700/50">
                <p className="text-[10px] text-gray-500 font-mono">Model: {model_version}</p>
              </div>
            )}
          </div>
        </div>

        {policy_decision && (
          <div className="glass-panel p-5 col-span-2 border-brand-500/30">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
              <ShieldAlert size={16} className="text-brand-500" /> Deterministic Policy
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-400 mb-1">Final Action</p>
                <span className={`badge ${policy_decision.action === 'HOLD' ? 'badge-danger' :
                  policy_decision.action === 'ENHANCED_VERIFICATION' ? 'badge-warning' :
                    policy_decision.action === 'MANUAL_REVIEW' ? 'badge-neutral' : 'badge-success'
                  }`}>
                  {policy_decision.action}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Grounding / AI Status</p>
                <span className={`text-sm font-medium ${policy_decision.grounding_status === 'SAFE' ? 'text-success-500' :
                  policy_decision.grounding_status === 'AI_UNAVAILABLE' ? 'text-danger-500' : 'text-warning-500'
                  }`}>
                  {policy_decision.grounding_status}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Economics</p>
                <div className="text-sm text-gray-300 font-mono">
                  Exp. Loss: ${policy_decision.expected_fraud_loss?.toFixed(2)}<br />
                  Intervention: ${policy_decision.intervention_cost?.toFixed(2)}<br />
                  Total Cost: ${policy_decision.expected_total_cost?.toFixed(2)}
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Reason Codes</p>
                <div className="flex flex-wrap gap-1">
                  {policy_decision.reason_codes.map(rc => (
                    <span key={rc} className="text-[10px] bg-gray-700 px-1.5 py-0.5 rounded text-gray-300">{rc}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel p-5">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Activity size={16} className="text-brand-500" /> Related Signals ({signals.length})
          </h3>
          <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
            {signals.map(sig => (
              <div key={sig.signal_id} className="p-3 bg-gray-800/50 rounded border border-gray-700/50">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono text-xs font-bold text-gray-200">{sig.transaction_id}</span>
                  <span className="text-[10px] text-brand-400 bg-brand-900 px-1.5 py-0.5 rounded">{sig.signal_type}</span>
                </div>
                <div className="flex justify-between text-[10px] text-gray-400">
                  <span>{new Date(sig.timestamp).toLocaleString()}</span>
                  <span>Score: {sig.risk_score?.toFixed(4) || 'N/A'}</span>
                </div>
                {sig.details && (
                  <div className="mt-2 pt-2 border-t border-gray-700/30 space-y-1">
                    {sig.details.detector_version && (
                      <div className="text-[10px] text-gray-400 font-mono">Detector: {sig.details.detector_version}</div>
                    )}
                    {sig.details.triggered_signals && sig.details.triggered_signals.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {sig.details.triggered_signals.map(ts => (
                          <span key={ts} className="text-[9px] bg-gray-700/50 px-1 rounded text-gray-300">{ts}</span>
                        ))}
                      </div>
                    )}
                    {sig.signal_type === 'MERCHANT_SPIKE' && sig.details.rate_multiplier && (
                      <div className="text-[10px] text-warning-400">Spike: {sig.details.rate_multiplier.toFixed(1)}x baseline</div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {signals.length === 0 && <p className="text-sm text-gray-500">No related signals found.</p>}
          </div>
        </div>

        <div className="glass-panel p-5">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
            <UserCheck size={16} className="text-brand-500" /> Analyst Disposition
          </h3>
          {status === 'CLOSED' ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-gray-400">Final Disposition</p>
                <p className="text-lg font-bold text-gray-100 mt-1">{disposition}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Analyst Notes</p>
                <p className="text-sm text-gray-300 mt-1 p-3 bg-gray-800/50 rounded border border-gray-700/50">{analyst_notes}</p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleDispositionSubmit} className="space-y-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Disposition</label>
                <select
                  className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-gray-200 focus:border-brand-500 focus:outline-none"
                  value={dispositionForm.disposition}
                  onChange={e => setDispositionForm({ ...dispositionForm, disposition: e.target.value })}
                  disabled={submittingDisposition}
                >
                  <option value="CONFIRMED_ABUSE">Confirmed Abuse</option>
                  <option value="FALSE_POSITIVE">False Positive</option>
                  <option value="MONITORED">Monitored</option>
                  <option value="ESCALATED">Escalated</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Notes</label>
                <textarea
                  className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-gray-200 focus:border-brand-500 focus:outline-none h-20"
                  placeholder="Enter investigation notes..."
                  value={dispositionForm.notes}
                  onChange={e => setDispositionForm({ ...dispositionForm, notes: e.target.value })}
                  disabled={submittingDisposition}
                  required
                ></textarea>
              </div>
              <button
                type="submit"
                className="btn btn-primary w-full"
                disabled={submittingDisposition}
              >
                {submittingDisposition ? 'Submitting...' : 'Submit Disposition'}
              </button>
            </form>
          )}
        </div>
      </div>

      {investigation_status !== 'UNINVESTIGATED' && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                <Cpu size={18} className="text-brand-500" /> Agentic Investigation
              </h2>

              <div className="glass-card p-4">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Audit Timeline</h3>
                <div className="space-y-4 font-mono text-xs text-gray-300 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-gray-700 before:to-transparent">

                  {/* Case Created */}
                  <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-5 h-5 rounded-full border-2 border-gray-900 bg-gray-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow"></div>
                    <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1.5rem)] p-2 rounded border border-gray-700/50 bg-gray-800/50">
                      <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                        <span>Case Initialized</span>
                        <span>{new Date(created_at).toLocaleTimeString()}</span>
                      </div>
                      <div className="font-bold text-gray-300 text-[10px]">Candidate D Risk Score: {risk_score?.toFixed(4)}</div>
                    </div>
                  </div>

                  {/* Tool Trace Timeline */}
                  {actualTools?.map((t, i) => (
                    <div key={i} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                      <div className={`flex items-center justify-center w-5 h-5 rounded-full border-2 border-gray-900 ${t.tool ? 'bg-brand-500' : 'bg-success-500'} shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow`}></div>
                      <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1.5rem)] p-2 rounded border border-gray-700/50 bg-gray-800/50">
                        <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                          <span>{t.tool ? 'Agent Action' : 'Agent Decision'}</span>
                        </div>
                        {t.tool ? (
                          <div className="text-[10px]"><span className="text-brand-400 font-bold">{t.tool}</span><br />Args: {JSON.stringify(t.args)}</div>
                        ) : (
                          <div className="text-success-400 font-bold text-[10px]">{t.reason}</div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* AI Synthesis */}
                  {investigation_status !== 'UNINVESTIGATED' && (
                    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                      <div className={`flex items-center justify-center w-5 h-5 rounded-full border-2 border-gray-900 ${ai_dossier ? 'bg-brand-400' : 'bg-danger-500'} shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow`}></div>
                      <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1.5rem)] p-2 rounded border border-gray-700/50 bg-gray-800/50">
                        <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                          <span>Synthesis Phase</span>
                        </div>
                        {ai_dossier ? (
                          <div className="text-[10px] text-brand-300">Generative AI Dossier & Grounding Completed</div>
                        ) : (
                          <div className="text-[10px] text-danger-400">AI UNAVAILABLE - FALLBACK ACTIVE</div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Policy Decision */}
                  {policy_decision && (
                    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                      <div className="flex items-center justify-center w-5 h-5 rounded-full border-2 border-gray-900 bg-gray-200 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow"></div>
                      <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1.5rem)] p-2 rounded border border-gray-700/50 bg-gray-800/50">
                        <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                          <span>Policy Enforcement</span>
                        </div>
                        <div className="text-[10px] text-gray-200 font-bold">Action: {policy_decision.action}</div>
                      </div>
                    </div>
                  )}

                </div>
              </div>

              <div className="glass-card p-4">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Evidence Gathered</h3>
                <div className="space-y-3">
                  {actualEvidence?.map((ev, i) => (
                    <div key={i} className="p-3 bg-gray-800/50 rounded border border-gray-700/50">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-mono text-xs font-bold text-gray-200">{ev.evidence_id}</span>
                        <span className="text-xs text-brand-400 bg-brand-900 px-1.5 py-0.5 rounded">{ev.source_tool}</span>
                      </div>
                      <pre className="text-[10px] text-gray-400 overflow-x-auto">
                        {JSON.stringify(ev.observation, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                <FileText size={18} className="text-brand-500" /> AI Dossier & Network
              </h2>

              <div className="glass-panel overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/80">
                  <h3 className="text-sm font-medium text-gray-200">Network Evidence Graph</h3>
                </div>
                <div className="p-2">
                  <NetworkGraph evidenceBundle={actualEvidence} />
                </div>
              </div>

              {ai_dossier ? (
                <div className="glass-card p-5 space-y-4">
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Facts</h4>
                    <ul className="space-y-1">
                      {ai_dossier.facts?.map(renderClaim)}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Inferences</h4>
                    <ul className="space-y-1">
                      {ai_dossier.inferences?.map(renderClaim)}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Unknowns</h4>
                    <ul className="space-y-1">
                      {ai_dossier.unknowns?.map(renderClaim)}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Risk Assessment</h4>
                    <p className="text-sm text-gray-300">{ai_dossier.risk_assessment}</p>
                  </div>
                </div>
              ) : (
                <div className="glass-card p-5 border-danger-500/30 bg-danger-900/10">
                  <div className="flex items-center gap-2 text-danger-500 mb-2">
                    <AlertCircle size={18} />
                    <h3 className="font-bold">AI UNAVAILABLE</h3>
                  </div>
                  <p className="text-sm text-gray-300">
                    Generative AI synthesis failed or was unavailable.
                    <br /><br />
                    <span className="font-semibold text-warning-500">FALLBACK MODE ACTIVE</span>: The system has proceeded using the deterministic policy engine evaluating raw evidence directly.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="glass-panel p-5 mt-6">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
              <List size={16} className="text-brand-500" /> Audit Log
            </h3>
            <div className="space-y-2 max-h-64 overflow-y-auto pr-2">
              {auditLog.map(log => (
                <div key={log.log_id} className="flex gap-4 p-3 bg-gray-800/30 rounded border border-gray-700/30 text-sm">
                  <div className="text-gray-500 font-mono text-xs whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </div>
                  <div>
                    <p className="text-gray-300">
                      <span className="font-semibold text-brand-400">{log.actor}</span> triggered <span className="font-mono text-xs bg-gray-700 px-1 rounded">{log.event_type}</span>
                    </p>
                    {log.reason && <p className="text-xs text-gray-500 mt-1">{log.reason}</p>}
                  </div>
                </div>
              ))}
              {auditLog.length === 0 && <p className="text-sm text-gray-500">No audit logs found.</p>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
