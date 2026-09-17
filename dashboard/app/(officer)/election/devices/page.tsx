"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { Plus, RefreshCcw, ShieldCheck, ShieldAlert } from "lucide-react";
import { DeviceResponse } from "@/lib/types";

export default function DevicesPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [id, setId] = useState("");
  const [name, setName] = useState("");

  const loadDevices = async () => {
    if (!selectedElection) return;
    setLoading(true);
    try {
      const data = await api.getDevices(selectedElection.id, token);
      setDevices(data);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDevices();
  }, [selectedElection]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedElection) return;
    setLoading(true);
    try {
      await api.registerDevice(selectedElection.id, { id, name }, token);
      await loadDevices();
      setId(""); setName("");
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (deviceId: string, status: "ACTIVE" | "SUSPENDED" | "REVOKED") => {
    setLoading(true);
    try {
      await api.updateDeviceStatus(selectedElection!.id, deviceId, status, token);
      await loadDevices();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view devices.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Device Management</h1>
        <button onClick={loadDevices} disabled={loading} className="text-slate-400 hover:text-white p-2">
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">Register New Device</h2>
        <form onSubmit={handleRegister} className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
          <div className="col-span-2">
            <label className="block text-xs font-medium text-slate-400 mb-1">Device ID</label>
            <input type="text" required value={id} onChange={e => setId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-slate-400 mb-1">Device Name</label>
            <input type="text" required value={name} onChange={e => setName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200" />
          </div>
          <button type="submit" disabled={loading}
            className="col-span-1 bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded-md font-medium flex items-center justify-center gap-2">
            <Plus className="w-4 h-4" /> Register
          </button>
        </form>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
            <tr>
              <th className="px-6 py-3 font-medium">Device Info</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Votes Cast</th>
              <th className="px-6 py-3 font-medium">Last Seen</th>
              <th className="px-6 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {devices.length ? (
              devices.map((d: any) => (
                <tr key={d.id} className="hover:bg-slate-800/20">
                  <td className="px-6 py-4">
                    <div className="font-medium text-slate-200">{d.name || d.id}</div>
                    <div className="font-mono text-[10px] text-slate-500">{d.id}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {d.status === 'ACTIVE' ? <ShieldCheck className="w-4 h-4 text-emerald-500" /> : <ShieldAlert className="w-4 h-4 text-rose-500" />}
                      <span className={`text-[11px] font-bold ${d.status === 'ACTIVE' ? 'text-emerald-500' : d.status === 'SUSPENDED' ? 'text-amber-500' : 'text-rose-500'}`}>
                        {d.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 font-mono text-emerald-400">{d.votes_cast || 0}</td>
                  <td className="px-6 py-4 text-xs text-slate-400">{d.last_seen ? new Date(d.last_seen).toLocaleString() : 'Never'}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      {d.status !== 'ACTIVE' && (
                        <button onClick={() => handleStatusUpdate(d.id, 'ACTIVE')} className="px-2 py-1 bg-emerald-500/10 text-emerald-500 rounded text-xs">Activate</button>
                      )}
                      {d.status === 'ACTIVE' && (
                        <button onClick={() => handleStatusUpdate(d.id, 'SUSPENDED')} className="px-2 py-1 bg-amber-500/10 text-amber-500 rounded text-xs">Suspend</button>
                      )}
                      {d.status !== 'REVOKED' && (
                        <button onClick={() => handleStatusUpdate(d.id, 'REVOKED')} className="px-2 py-1 bg-rose-500/10 text-rose-500 rounded text-xs">Revoke</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-slate-500">No devices registered.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
