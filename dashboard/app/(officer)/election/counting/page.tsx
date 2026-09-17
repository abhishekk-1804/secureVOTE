"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { Calculator, CheckCircle2, XCircle, RefreshCcw, FileText } from "lucide-react";

export default function CountingCenterPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!selectedElection) return;
    setLoading(true);
    try {
      const data = await api.getResults(selectedElection.id, token);
      setResults(data);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedElection]);

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view counting center.</div>;
  }

  const isClosed = selectedElection.state === "CLOSED" || selectedElection.state === "PUBLISHED";
  const totalCandidateVotes = results?.candidate_results?.reduce((acc: number, curr: any) => acc + curr.votes, 0) || 0;
  const totalDeviceVotes = results?.device_results?.reduce((acc: number, curr: any) => acc + curr.votes_counted, 0) || 0;
  const isReconciled = totalCandidateVotes === selectedElection.ballot_count && totalDeviceVotes === selectedElection.ballot_count;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Calculator className="w-6 h-6 text-blue-500" />
          Counting Center
        </h1>
        <button onClick={loadData} disabled={loading} className="text-slate-400 hover:text-white p-2">
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {!isClosed && (
        <div className="bg-amber-500/10 border border-amber-500/50 text-amber-500 p-4 rounded-lg flex items-center gap-3 text-sm">
          <span className="relative flex h-3 w-3"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span></span>
          Election is currently {selectedElection.state}. Counting totals are partial and subject to change.
        </div>
      )}

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-6">Candidate Totals</h2>
            {results?.candidate_results ? (
              <div className="space-y-4">
                {results.candidate_results.map((c: any) => {
                  const percent = totalCandidateVotes > 0 ? (c.votes / totalCandidateVotes) * 100 : 0;
                  return (
                    <div key={c.candidate_id}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-slate-200">{c.candidate_name || c.candidate_id}</span>
                        <span className="font-mono text-emerald-400">{c.votes} ({percent.toFixed(1)}%)</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full transition-all" style={{ width: `${percent}%` }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center text-slate-500 py-4">No results available yet.</div>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">Device Contributions</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {results?.device_results?.map((d: any) => (
                <div key={d.device_id} className="bg-slate-950 border border-slate-800 p-4 rounded-lg flex justify-between items-center">
                  <div>
                    <div className="font-medium text-sm text-slate-300">Device {d.device_id.substring(0,8)}...</div>
                    <div className="text-xs text-slate-500 mt-1">Hash: {d.last_hash ? d.last_hash.substring(0,8) + '...' : 'N/A'}</div>
                  </div>
                  <div className="text-xl font-bold font-mono text-emerald-400">{d.votes_counted}</div>
                </div>
              ))}
              {!results?.device_results?.length && (
                <div className="col-span-2 text-center text-slate-500 py-2">No device data available.</div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">Reconciliation</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                <span className="text-sm text-slate-400">Total Ballots Cast</span>
                <span className="font-mono font-bold text-lg">{selectedElection.ballot_count}</span>
              </div>
              <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                <span className="text-sm text-slate-400">Sum of Candidate Totals</span>
                <span className="font-mono font-bold text-lg">{totalCandidateVotes}</span>
              </div>
              <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                <span className="text-sm text-slate-400">Sum of Device Totals</span>
                <span className="font-mono font-bold text-lg">{totalDeviceVotes}</span>
              </div>
              <div className={`p-3 rounded-lg flex items-center justify-center gap-2 font-medium ${isReconciled ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
                {isReconciled ? <><CheckCircle2 className="w-5 h-5" /> MATCH</> : <><XCircle className="w-5 h-5" /> MISMATCH</>}
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">Verification Checkpoints</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                {results?.manifest_hash ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <div className="w-4 h-4 rounded-full border border-slate-600" />}
                <span className="text-sm text-slate-300">Manifest Generated</span>
              </div>
              <div className="flex items-center gap-3">
                {isReconciled ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <div className="w-4 h-4 rounded-full border border-slate-600" />}
                <span className="text-sm text-slate-300">Counts Reconciled</span>
              </div>
              <div className="flex items-center gap-3">
                {selectedElection.state === 'PUBLISHED' ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <div className="w-4 h-4 rounded-full border border-slate-600" />}
                <span className="text-sm text-slate-300">Results Published</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
