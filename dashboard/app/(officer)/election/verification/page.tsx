"use client";
import React, { useState } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { CheckCircle, ShieldAlert, Play, Link as LinkIcon, PenTool } from "lucide-react";

export default function VerificationPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const handleVerify = async () => {
    if (!selectedElection) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.runVerification(selectedElection.id, token);
      setResult(data);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSign = async () => {
    if (!selectedElection) return;
    setLoading(true);
    try {
      await api.signElectionManifest(selectedElection.id, token);
      await handleVerify();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view verification.</div>;
  }

  const overallPassed = result?.is_valid;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <CheckCircle className="w-6 h-6 text-blue-500" />
          Independent Verification
        </h1>
        <button
          onClick={handleVerify}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded-md font-medium flex items-center gap-2 disabled:opacity-50"
        >
          <Play className="w-4 h-4" /> Run Verifier
        </button>
      </div>

      <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-4 text-sm text-slate-300">
        This tool recalculates all election cryptographic proofs from the raw immutable storage. It does not rely on cached database state.
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className={`p-6 rounded-lg border ${overallPassed ? 'bg-emerald-500/10 border-emerald-500/50' : 'bg-rose-500/10 border-rose-500/50'}`}>
              <h2 className={`text-xl font-bold mb-2 flex items-center gap-2 ${overallPassed ? 'text-emerald-400' : 'text-rose-400'}`}>
                {overallPassed ? <CheckCircle className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
                Verification {overallPassed ? 'PASSED' : 'FAILED'}
              </h2>
              <p className={`text-sm ${overallPassed ? 'text-emerald-500/80' : 'text-rose-500/80'}`}>
                {overallPassed ? 'All cryptographic properties hold. The election result is mathematically proven.' : 'One or more cryptographic properties failed verification. The election result cannot be trusted.'}
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              <h2 className="text-lg font-medium mb-4">Verification Checkpoints</h2>
              <div className="space-y-4">
                {[
                  { name: 'Configuration Hash Match', passed: result.checks?.config_hash_valid },
                  { name: 'Audit Chain Integrity', passed: result.checks?.audit_chain_valid },
                  { name: 'Ballot Reconciliation', passed: result.checks?.reconciliation_valid },
                  { name: 'Tally Verification', passed: result.checks?.tally_valid }
                ].map((check, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <span className="text-sm font-medium text-slate-300">{check.name}</span>
                    {check.passed === undefined ? (
                      <span className="text-slate-500 text-xs font-bold">N/A</span>
                    ) : check.passed ? (
                      <span className="text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded text-xs font-bold flex items-center gap-1"><CheckCircle className="w-3 h-3" /> PASS</span>
                    ) : (
                      <span className="text-rose-500 bg-rose-500/10 px-2 py-1 rounded text-xs font-bold flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> FAIL</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-medium flex items-center gap-2"><PenTool className="w-5 h-5 text-blue-400" /> Digital Signatures</h2>
                <button onClick={handleSign} disabled={loading || !overallPassed} className="bg-slate-800 hover:bg-slate-700 text-slate-300 py-1.5 px-3 rounded text-xs font-medium disabled:opacity-50">
                  Sign Manifest
                </button>
              </div>
              <div className="space-y-4 text-sm">
                <div>
                  <div className="text-slate-500 mb-1">Manifest Hash</div>
                  <div className="font-mono text-xs text-blue-400 break-all">{result.manifest_hash || "N/A"}</div>
                </div>
                <div>
                  <div className="text-slate-500 mb-1">Officer Signature</div>
                  {result.signature ? (
                    <div className="font-mono text-xs text-emerald-400 break-all bg-emerald-950/30 p-2 rounded border border-emerald-900/50">
                      {result.signature}
                    </div>
                  ) : (
                    <div className="text-slate-500 italic">No signature found</div>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              <h2 className="text-lg font-medium mb-4 flex items-center gap-2"><LinkIcon className="w-5 h-5 text-blue-400" /> Blockchain Anchors</h2>
              <div className="text-center py-6 text-slate-500 text-sm">
                Blockchain anchoring feature is configured but no anchors have been published for this election yet.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
