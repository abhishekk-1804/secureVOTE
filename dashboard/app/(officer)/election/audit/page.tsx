"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { ScrollText, ShieldCheck, RefreshCcw, Filter, AlertTriangle } from "lucide-react";

export default function AuditPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verifyStatus, setVerifyStatus] = useState<any>(null);

  const loadData = async () => {
    if (!selectedElection) return;
    setLoading(true);
    try {
      const data = await api.getAuditLog(selectedElection.id, token);
      setEvents(data);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedElection]);

  const handleVerifyChain = async () => {
    if (!selectedElection) return;
    setLoading(true);
    setVerifyStatus(null);
    try {
      const data = await api.verifyAuditChain(selectedElection.id, token);
      setVerifyStatus(data);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view audit logs.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <ScrollText className="w-6 h-6 text-blue-500" />
            Audit Explorer
          </h1>
          <div className="mt-1 flex items-center gap-2">
            <span className="bg-slate-800 text-slate-300 text-[10px] uppercase font-bold px-2 py-0.5 rounded tracking-wider border border-slate-700">
              TAMPER-EVIDENT AUDIT TRAIL
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleVerifyChain} disabled={loading} className="bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 px-4 rounded-md font-medium flex items-center gap-2 disabled:opacity-50 text-sm">
            <ShieldCheck className="w-4 h-4" /> Verify Chain
          </button>
          <button onClick={loadData} disabled={loading} className="bg-slate-800 hover:bg-slate-700 text-slate-200 p-2 rounded-md disabled:opacity-50">
            <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      {verifyStatus && (
        <div className={`p-4 rounded-lg flex items-start gap-3 border ${verifyStatus.is_valid ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400' : 'bg-rose-500/10 border-rose-500/50 text-rose-400'}`}>
          {verifyStatus.is_valid ? <ShieldCheck className="w-5 h-5 shrink-0" /> : <AlertTriangle className="w-5 h-5 shrink-0" />}
          <div>
            <h3 className="font-bold">{verifyStatus.is_valid ? 'Audit Chain Verified' : 'Audit Chain Broken'}</h3>
            <p className="text-sm opacity-90 mt-1">Checked {verifyStatus.events_checked} events.</p>
            {!verifyStatus.is_valid && verifyStatus.broken_at_seq && (
              <p className="text-sm font-bold mt-2">Broken at sequence {verifyStatus.broken_at_seq}</p>
            )}
          </div>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <div className="p-3 border-b border-slate-800 bg-slate-950 flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Filter className="w-4 h-4" /> Filters:
          </div>
          <select className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-300">
            <option value="">All Event Types</option>
            <option value="ELECTION_CREATED">Election Created</option>
            <option value="DEVICE_REGISTERED">Device Registered</option>
            <option value="BALLOT_CAST">Ballot Cast</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-6 py-3 font-medium">Seq</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Actor</th>
                <th className="px-6 py-3 font-medium">Device</th>
                <th className="px-6 py-3 font-medium">Timestamp</th>
                <th className="px-6 py-3 font-medium">Hash</th>
                <th className="px-6 py-3 font-medium">Prev Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {events.length ? (
                events.map(e => (
                  <tr key={e.id} className="hover:bg-slate-800/20">
                    <td className="px-6 py-3 font-mono text-xs">{e.sequence_number}</td>
                    <td className="px-6 py-3">
                      <span className="text-[10px] font-bold bg-slate-800 text-blue-400 px-2 py-1 rounded">
                        {e.event_type}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-xs">{e.actor_id || '-'}</td>
                    <td className="px-6 py-3 text-xs font-mono">{e.device_id || '-'}</td>
                    <td className="px-6 py-3 text-xs text-slate-400">{new Date(e.timestamp).toLocaleString()}</td>
                    <td className="px-6 py-3 font-mono text-[10px] text-emerald-400" title={e.hash}>{e.hash?.substring(0,8)}...</td>
                    <td className="px-6 py-3 font-mono text-[10px] text-slate-500" title={e.previous_hash}>{e.previous_hash ? e.previous_hash.substring(0,8) + '...' : 'GENESIS'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-500">No audit events found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
