"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { Plus, RefreshCcw } from "lucide-react";

export default function PollingStationsPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [stations, setStations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [constituency, setConstituency] = useState("");
  const [location, setLocation] = useState("");
  const [officer, setOfficer] = useState("");

  const loadStations = async () => {
    if (!selectedElection) return;
    setLoading(true);
    try {
      const data = await api.getPollingStations(selectedElection.id, token);
      setStations(data);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStations();
  }, [selectedElection]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedElection) return;
    setLoading(true);
    try {
      await api.createPollingStation(selectedElection.id, {
        station_code: code,
        name,
        constituency,
        location,
        officer_name: officer || undefined,
      }, token);
      await loadStations();
      setCode(""); setName(""); setConstituency(""); setLocation(""); setOfficer("");
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view polling stations.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Polling Stations</h1>
        <button onClick={loadStations} disabled={loading} className="text-slate-400 hover:text-white p-2">
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">Register Station</h2>
        <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-6 gap-4 items-end">
          <div className="col-span-1">
            <label className="block text-xs font-medium text-slate-400 mb-1">Code</label>
            <input type="text" required value={code} onChange={e => setCode(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-slate-400 mb-1">Name</label>
            <input type="text" required value={name} onChange={e => setName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200" />
          </div>
          <div className="col-span-1">
            <label className="block text-xs font-medium text-slate-400 mb-1">Constituency</label>
            <input type="text" required value={constituency} onChange={e => setConstituency(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200" />
          </div>
          <div className="col-span-1">
            <label className="block text-xs font-medium text-slate-400 mb-1">Officer</label>
            <input type="text" value={officer} onChange={e => setOfficer(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200" />
          </div>
          <button type="submit" disabled={loading}
            className="col-span-1 bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded-md font-medium flex items-center justify-center gap-2">
            <Plus className="w-4 h-4" /> Add
          </button>
        </form>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
            <tr>
              <th className="px-6 py-3 font-medium">Code</th>
              <th className="px-6 py-3 font-medium">Name</th>
              <th className="px-6 py-3 font-medium">Constituency</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Officer</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {stations.length ? (
              stations.map(s => (
                <tr key={s.id} className="hover:bg-slate-800/20">
                  <td className="px-6 py-4 font-mono text-xs">{s.code}</td>
                  <td className="px-6 py-4 font-medium">{s.name}</td>
                  <td className="px-6 py-4">{s.constituency}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-[10px] font-bold ${s.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-slate-800 text-slate-400'}`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">{s.officer_in_charge || '-'}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-slate-500">No polling stations configured.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
