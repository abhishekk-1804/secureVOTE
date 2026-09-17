"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { ShieldAlert, AlertOctagon, Info, RefreshCcw, CreditCard } from "lucide-react";

export default function SecurityCenterPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [rfidData, setRfidData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!selectedElection) return;
    setLoading(true);
    try {
      const data = await api.getElectionAnomalies(selectedElection.id, token);
      setAnomalies(data.findings);
      const rfid = await api.getRFIDDemoCards();
      setRfidData(rfid);
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
    return <div className="p-8 text-center text-slate-400">Select an election to view security center.</div>;
  }

  const getSeverityColor = (sev: string) => {
    if (sev === "HIGH") return "bg-rose-500/10 text-rose-500 border-rose-500/30";
    if (sev === "MEDIUM") return "bg-amber-500/10 text-amber-500 border-amber-500/30";
    return "bg-blue-500/10 text-blue-400 border-blue-500/30";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <ShieldAlert className="w-6 h-6 text-rose-500" />
          Security Center
        </h1>
        <button onClick={loadData} disabled={loading} className="bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 px-4 rounded-md font-medium flex items-center gap-2 disabled:opacity-50 text-sm">
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh Scans
        </button>
      </div>

      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex items-start gap-3 text-sm text-amber-500">
        <Info className="w-5 h-5 shrink-0 mt-0.5" />
        <div>
          <h3 className="font-bold">Anomaly detection is ADVISORY ONLY</h3>
          <p className="mt-1 opacity-90">Statistical anomalies and heuristic alerts do not override cryptographic proofs. They are provided to guide physical investigations and process improvements.</p>
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-950">
              <h2 className="text-lg font-medium flex items-center gap-2"><AlertOctagon className="w-5 h-5 text-rose-400" /> Detected Anomalies</h2>
            </div>
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3 font-medium">Type</th>
                  <th className="px-6 py-3 font-medium">Severity</th>
                  <th className="px-6 py-3 font-medium">Description</th>
                  <th className="px-6 py-3 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {anomalies.length ? (
                  anomalies.map((a, i) => (
                    <tr key={i} className="hover:bg-slate-800/20">
                      <td className="px-6 py-3 font-medium text-slate-300">{a.type}</td>
                      <td className="px-6 py-3">
                        <span className={`px-2 py-1 rounded text-[10px] font-bold border ${getSeverityColor(a.severity)}`}>
                          {a.severity}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-slate-400 text-xs">{a.description}</td>
                      <td className="px-6 py-3 text-xs text-slate-500">{new Date(a.timestamp).toLocaleString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-slate-500">No anomalies detected.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4 flex items-center gap-2"><CreditCard className="w-5 h-5 text-blue-400" /> RFID Pseudonymization Demo</h2>
            <div className="text-sm text-slate-400 mb-4">
              {rfidData?.boundary_notice || "RFID tags are pseudonymous and cannot be linked back to voters."}
            </div>
            <div className="space-y-3">
              {rfidData?.cards?.map((c: any, i: number) => (
                <div key={i} className="bg-slate-950 border border-slate-800 p-3 rounded-lg text-xs">
                  <div className="flex justify-between mb-1">
                    <span className="text-slate-500">ID Number:</span>
                    <span className="text-slate-300">{c.id_number}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">RFID Data (Hashed):</span>
                    <span className="font-mono text-emerald-400">{c.rfid_data.substring(0, 16)}...</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
