"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api-client";
import { DeviceResponse, DeviceStatus, ElectionResponse } from "@/lib/types";
import { StatusBadge } from "@/components/common/StatusBadge";
import { AlertBanner } from "@/components/common/AlertBanner";
import {
  Cpu,
  Plus,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  PauseCircle,
  Ban,
  X,
} from "lucide-react";

export default function DevicesPage() {
  const { token, role } = useAuth();
  const [elections, setElections] = useState<ElectionResponse[]>([]);
  const [selectedElectionId, setSelectedElectionId] = useState<string>("EV-2026-001");
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Register Modal state
  const [showRegisterModal, setShowRegisterModal] = useState<boolean>(false);
  const [newDeviceId, setNewDeviceId] = useState<string>("EVM-005");
  const [newDeviceName, setNewDeviceName] = useState<string>("Precinct 5 Voting Terminal");

  const fetchDevices = async (electionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const all = await api.getElections(token);
      setElections(all);
      const target = all.find((e) => e.id === electionId) || all[0];
      if (target) {
        setSelectedElectionId(target.id);
        const devList = await api.getDevices(target.id, token);
        setDevices(devList);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load registered hardware devices");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices(selectedElectionId);
  }, [token]);

  const handleUpdateStatus = async (deviceId: string, newStatus: DeviceStatus) => {
    if (!token) return;
    if (role !== "ADMIN") {
      setError("Forbidden: Only ADMIN users may modify hardware device status.");
      return;
    }
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await api.updateDeviceStatus(selectedElectionId, deviceId, newStatus, token);
      setSuccessMsg(`Device ${deviceId} status changed to ${newStatus}`);
      await fetchDevices(selectedElectionId);
    } catch (err: any) {
      setError(err.message || `Failed to update device ${deviceId}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRegisterDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setActionLoading(true);
    setError(null);
    try {
      await api.registerDevice(
        selectedElectionId,
        { id: newDeviceId, name: newDeviceName },
        token
      );
      setShowRegisterModal(false);
      setSuccessMsg(`Device ${newDeviceId} successfully registered.`);
      await fetchDevices(selectedElectionId);
    } catch (err: any) {
      setError(err.message || "Device registration failed");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Device Management
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Registered EVM units, monotonic sequence tracking, and hardware state lifecycle
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedElectionId}
            onChange={(e) => {
              setSelectedElectionId(e.target.value);
              fetchDevices(e.target.value);
            }}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
          >
            {elections.map((el) => (
              <option key={el.id} value={el.id}>
                {el.id} — {el.title}
              </option>
            ))}
          </select>

          {role === "ADMIN" && (
            <button
              onClick={() => setShowRegisterModal(true)}
              className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow transition"
            >
              <Plus className="w-3.5 h-3.5" />
              Register Unit
            </button>
          )}

          <button
            onClick={() => fetchDevices(selectedElectionId)}
            disabled={loading}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
            title="Refresh"
            aria-label="Refresh devices"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <AlertBanner
          type="error"
          title="Device Service Notice"
          message={error}
          onDismiss={() => setError(null)}
        />
      )}

      {successMsg && (
        <AlertBanner
          type="success"
          title="Success"
          message={successMsg}
          onDismiss={() => setSuccessMsg(null)}
        />
      )}

      {/* Devices Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4">Device ID</th>
                <th className="py-3 px-4">Terminal Name</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Last Sequence</th>
                <th className="py-3 px-4">Votes Cast</th>
                <th className="py-3 px-4">Last Seen</th>
                {role === "ADMIN" && <th className="py-3 px-4 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {devices.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                    No hardware devices registered for this election.
                  </td>
                </tr>
              ) : (
                devices.map((device) => (
                  <tr
                    key={device.id}
                    className="hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="py-3 px-4 font-mono font-bold text-blue-400 text-xs">
                      {device.id}
                    </td>
                    <td className="py-3 px-4 font-medium text-white">
                      {device.name}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={device.status} />
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-200">
                      #{device.last_sequence_number}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-slate-200">
                      {device.total_votes_cast}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {device.last_seen_at
                        ? new Date(device.last_seen_at).toLocaleTimeString()
                        : "Never"}
                    </td>
                    {role === "ADMIN" && (
                      <td className="py-3 px-4 text-right space-x-1.5">
                        {device.status === "REGISTERED" && (
                          <button
                            disabled={actionLoading}
                            onClick={() => handleUpdateStatus(device.id, "ACTIVE")}
                            className="px-2 py-1 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 border border-emerald-500/30 rounded text-[11px] font-medium transition"
                          >
                            Activate
                          </button>
                        )}
                        {device.status === "ACTIVE" && (
                          <>
                            <button
                              disabled={actionLoading}
                              onClick={() => handleUpdateStatus(device.id, "SUSPENDED")}
                              className="px-2 py-1 bg-amber-600/20 text-amber-400 hover:bg-amber-600/30 border border-amber-500/30 rounded text-[11px] font-medium transition"
                            >
                              Suspend
                            </button>
                            <button
                              disabled={actionLoading}
                              onClick={() => handleUpdateStatus(device.id, "REVOKED")}
                              className="px-2 py-1 bg-rose-600/20 text-rose-400 hover:bg-rose-600/30 border border-rose-500/30 rounded text-[11px] font-medium transition"
                            >
                              Revoke
                            </button>
                          </>
                        )}
                        {device.status === "SUSPENDED" && (
                          <>
                            <button
                              disabled={actionLoading}
                              onClick={() => handleUpdateStatus(device.id, "ACTIVE")}
                              className="px-2 py-1 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 border border-emerald-500/30 rounded text-[11px] font-medium transition"
                            >
                              Re-activate
                            </button>
                            <button
                              disabled={actionLoading}
                              onClick={() => handleUpdateStatus(device.id, "REVOKED")}
                              className="px-2 py-1 bg-rose-600/20 text-rose-400 hover:bg-rose-600/30 border border-rose-500/30 rounded text-[11px] font-medium transition"
                            >
                              Revoke
                            </button>
                          </>
                        )}
                        {device.status === "REVOKED" && (
                          <span className="text-[11px] text-slate-500 italic">
                            Terminal (Non-reversible)
                          </span>
                        )}
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Register Device Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Cpu className="w-4 h-4 text-blue-400" />
                Register New EVM Terminal
              </h3>
              <button
                onClick={() => setShowRegisterModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleRegisterDevice} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Device ID (Format: EVM-XXX)
                </label>
                <input
                  type="text"
                  value={newDeviceId}
                  onChange={(e) => setNewDeviceId(e.target.value)}
                  pattern="^EVM-\d{3}$"
                  required
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Terminal Name / Precinct Location
                </label>
                <input
                  type="text"
                  value={newDeviceName}
                  onChange={(e) => setNewDeviceName(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold shadow"
                >
                  Register Unit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
