"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { BarChart3, Download, Trophy, FileText, CheckCircle2 } from "lucide-react";

export default function ResultsPage() {
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

  const handleExport = async () => {
    if (!selectedElection) return;
    try {
      const data = await api.exportElection(selectedElection.id, token);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `election-${selectedElection.id}-export.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(formatApiError(err));
    }
  };

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view results.</div>;
  }

  const isPublished = selectedElection.state === "PUBLISHED";
  const totalVotes = results?.candidate_results?.reduce((acc: number, curr: any) => acc + curr.votes, 0) || 0;

  // Find winner
  let winner = null;
  if (isPublished && results?.candidate_results?.length > 0) {
    winner = [...results.candidate_results].sort((a, b) => b.votes - a.votes)[0];
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-blue-500" />
          Election Results Record
        </h1>
        <button onClick={handleExport} disabled={!isPublished} className="bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 px-4 rounded-md font-medium flex items-center gap-2 disabled:opacity-50">
          <Download className="w-4 h-4" /> Export Data
        </button>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      {isPublished ? (
        <div className="bg-emerald-500/10 border border-emerald-500/50 p-6 rounded-lg flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-emerald-400 flex items-center gap-2"><Trophy className="w-5 h-5" /> Election Concluded</h2>
            <p className="text-sm text-emerald-500/80 mt-1">These results are final and cryptographically verified.</p>
          </div>
          {winner && (
            <div className="text-right">
              <div className="text-sm font-medium text-slate-400">Projected Winner</div>
              <div className="text-2xl font-bold text-emerald-400">{winner.candidate_name || winner.candidate_id}</div>
              <div className="text-sm text-slate-300">{winner.votes} votes ({(totalVotes > 0 ? (winner.votes / totalVotes) * 100 : 0).toFixed(1)}%)</div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-slate-800 border border-slate-700 p-6 rounded-lg text-center">
          <p className="text-slate-400">Results are not yet published. The election must be in the PUBLISHED state.</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3 font-medium">Candidate</th>
                  <th className="px-6 py-3 font-medium">Votes</th>
                  <th className="px-6 py-3 font-medium w-1/3">Percentage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {results?.candidate_results?.length ? (
                  results.candidate_results.map((c: any) => {
                    const percent = totalVotes > 0 ? (c.votes / totalVotes) * 100 : 0;
                    return (
                      <tr key={c.candidate_id} className="hover:bg-slate-800/20">
                        <td className="px-6 py-4 font-medium">{c.candidate_name || c.candidate_id}</td>
                        <td className="px-6 py-4 font-mono text-emerald-400">{c.votes}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <span className="w-12 text-right">{percent.toFixed(1)}%</span>
                            <div className="flex-1 bg-slate-800 rounded-full h-2">
                              <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${percent}%` }}></div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={3} className="px-6 py-8 text-center text-slate-500">No results available.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4 flex items-center gap-2"><FileText className="w-5 h-5 text-blue-400" /> Election Manifest</h2>
            <div className="space-y-4 text-sm">
              <div>
                <div className="text-slate-500 mb-1">Manifest Hash</div>
                <div className="font-mono text-xs text-blue-400 break-all bg-slate-950 p-2 rounded border border-slate-800">
                  {results?.manifest_hash || "Not generated"}
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-slate-800 pt-3">
                <span className="text-slate-400">Total Valid Ballots</span>
                <span className="font-mono font-bold">{selectedElection.ballot_count}</span>
              </div>
              <div className="flex items-center justify-between border-t border-slate-800 pt-3">
                <span className="text-slate-400">Signature Status</span>
                <span className="flex items-center gap-1 text-emerald-400 font-medium">
                  {results?.manifest_hash ? <><CheckCircle2 className="w-4 h-4" /> Signed</> : "Pending"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
