"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { RefreshCcw, Key, CheckCircle2, Copy } from "lucide-react";

export default function PollingPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [voterCredential, setVoterCredential] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [sessionToken, setSessionToken] = useState<string | null>(null);

  const loadData = async () => {
    if (!selectedElection) return;
    setLoading(true);
    try {
      const sess = await api.getSessions(selectedElection.id, token);
      setSessions(sess);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [selectedElection]);

  const handleAuthorize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedElection) return;
    setLoading(true);
    setError(null);
    setSessionToken(null);
    try {
      const res = await api.authorizeSession(selectedElection.id, { voter_credential: voterCredential, device_id: deviceId }, token);
      setSessionToken(res.session_token);
      setVoterCredential("");
      await loadData();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view polling.</div>;
  }

  const isOpen = selectedElection.state === "OPEN";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Polling Operations</h1>
        <button onClick={loadData} disabled={loading} className="text-slate-400 hover:text-white p-2">
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className={`p-4 rounded-lg flex items-center justify-between border ${isOpen ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400' : 'bg-amber-500/10 border-amber-500/50 text-amber-400'}`}>
        <div>
          <div className="text-sm font-bold uppercase tracking-wider mb-1">Polling Status: {selectedElection.state}</div>
          <div className="text-xs opacity-80">{isOpen ? 'Voters can currently cast ballots.' : 'Voting is currently paused or closed.'}</div>
        </div>
        <div className="flex items-center gap-6 text-right">
          <div>
            <div className="text-xs font-medium opacity-70">Active Sessions</div>
            <div className="text-xl font-bold">{sessions.filter(s => s.status === 'ACTIVE').length}</div>
          </div>
          <div>
            <div className="text-xs font-medium opacity-70">Total Votes</div>
            <div className="text-xl font-bold">{selectedElection.ballot_count}</div>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      {sessionToken && (
        <div className="bg-blue-600/10 border border-blue-500/50 rounded-lg p-6 text-center space-y-4">
          <div className="flex justify-center"><CheckCircle2 className="w-12 h-12 text-blue-500" /></div>
          <div>
            <h3 className="text-lg font-bold text-blue-400">Session Authorized</h3>
            <p className="text-sm text-blue-400/80 mt-1">Provide this token to the voter. It is valid for one use only.</p>
          </div>
          <div className="flex items-center justify-center gap-2">
            <code className="bg-blue-950 text-blue-200 px-4 py-2 rounded text-lg font-mono border border-blue-800">{sessionToken}</code>
            <button
              onClick={() => navigator.clipboard.writeText(sessionToken)}
              className="p-2 bg-blue-900/50 text-blue-300 hover:text-white rounded border border-blue-800"
              title="Copy token"
            >
              <Copy className="w-5 h-5" />
            </button>
          </div>
          <div className="text-xs font-bold text-amber-500 mt-4 bg-amber-500/10 inline-block px-3 py-1.5 rounded">
            WARNING: SESSION TOKEN - DO NOT LOG. DO NOT RECORD.
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4 flex items-center gap-2"><Key className="w-5 h-5 text-blue-400" /> Authorize Voter</h2>
            <form onSubmit={handleAuthorize} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Voter Credential (ID/Hash)</label>
                <input type="text" required value={voterCredential} onChange={e => setVoterCredential(e.target.value)} disabled={!isOpen || loading}
                  className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200 disabled:opacity-50" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Device ID</label>
                <input type="text" required value={deviceId} onChange={e => setDeviceId(e.target.value)} disabled={!isOpen || loading}
                  className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200 disabled:opacity-50" />
              </div>
              <button type="submit" disabled={!isOpen || loading}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded-md font-medium disabled:opacity-50 transition">
                Authorize Session
              </button>
            </form>
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden h-full">
            <div className="p-4 border-b border-slate-800 bg-slate-900 flex justify-between items-center">
              <h2 className="text-lg font-medium">Recent Sessions</h2>
            </div>
            <div className="overflow-y-auto max-h-[400px]">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 sticky top-0">
                  <tr>
                    <th className="px-6 py-3 font-medium">Device ID</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                    <th className="px-6 py-3 font-medium">Created At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {sessions.length ? (
                    sessions.map((s, i) => (
                      <tr key={i} className="hover:bg-slate-800/20">
                        <td className="px-6 py-3 font-mono text-xs">{s.device_id}</td>
                        <td className="px-6 py-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${s.status === 'ACTIVE' ? 'bg-blue-500/10 text-blue-500' : s.status === 'USED' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-slate-800 text-slate-400'}`}>
                            {s.status}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-xs text-slate-400">{new Date(s.created_at || Date.now()).toLocaleTimeString()}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="px-6 py-8 text-center text-slate-500">No active sessions.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
