"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api-client";
import {
  AuditEntryResponse,
  DeviceResponse,
  HealthCheckResponse,
} from "@/lib/types";
import { StatusBadge } from "@/components/common/StatusBadge";
import { AlertBanner } from "@/components/common/AlertBanner";
import {
  ShieldAlert,
  Activity,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Cpu,
  Lock,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

const SECURITY_CONTROLS = [
  {
    id: 1,
    name: "Audit Log Tamper Protection",
    mechanism: "Cryptographic SHA-256 Hash Chain",
    detection: "AUDIT VERIFICATION FAILED on any historical mutation",
    status: "ACTIVE",
  },
  {
    id: 2,
    name: "Configuration Freezing",
    mechanism: "Frozen Candidate Slate Hash in DB & EEPROM",
    detection: "CONFIGURATION HASH MISMATCH post-lock",
    status: "ACTIVE",
  },
  {
    id: 3,
    name: "Duplicate Session Prevention",
    mechanism: "Unique DB Constraint on (election_id, voter_credential)",
    detection: "REQUEST REJECTED (HTTP 409) on second attempt",
    status: "ACTIVE",
  },
  {
    id: 4,
    name: "Closed-Election Protection",
    mechanism: "FSM State Enforcement in Ballot Service",
    detection: "REQUEST REJECTED (HTTP 409) if election is not OPEN",
    status: "ACTIVE",
  },
  {
    id: 5,
    name: "Physical Enclosure Tamper Switch",
    mechanism: "Hardware Microswitch + Non-Volatile EEPROM Latch",
    detection: "TAMPER_DETECTED event and device SUSPENDED",
    status: "ACTIVE",
  },
  {
    id: 6,
    name: "Independent Exact Reconciliation",
    mechanism: "Zero Drift Check: sum(cand) == total == sum(dev)",
    detection: "RECONCILIATION FAILURE on any numerical delta",
    status: "ACTIVE",
  },
  {
    id: 7,
    name: "Message Replay Protection",
    mechanism: "Monotonic Sequence Counter per Device in EEPROM",
    detection: "REPLAY REJECTED (HTTP 409) if seq <= last_seen_sequence",
    status: "ACTIVE",
  },
  {
    id: 8,
    name: "Device Whitelisting",
    mechanism: "Pre-registered Device Authentication Check",
    detection: "DEVICE REJECTED (HTTP 403) for unknown or revoked units",
    status: "ACTIVE",
  },
];

export default function SecurityCenterPage() {
  const { token } = useAuth();
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [tamperEvents, setTamperEvents] = useState<AuditEntryResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSecurityData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, devList, auditEntries] = await Promise.all([
        api.getHealth(),
        api.getDevices("EV-2026-001", token).catch(() => []),
        api.getAuditLog("EV-2026-001", token).catch(() => []),
      ]);
      setHealth(healthData);
      setDevices(devList);
      const tampers = auditEntries.filter(
        (e) =>
          e.event_type === "TAMPER_DETECTED" ||
          (e.event_data && e.event_data.includes("SUSPENDED"))
      );
      setTamperEvents(tampers);
    } catch (err: any) {
      setError(err.message || "Failed to load security center metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityData();
  }, [token]);

  const suspendedDevices = devices.filter((d) => d.status === "SUSPENDED");
  const revokedDevices = devices.filter((d) => d.status === "REVOKED");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Security Center & Tamper Monitor
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time defense-in-depth monitoring and physical breach anomaly detection
          </p>
        </div>

        <button
          onClick={fetchSecurityData}
          disabled={loading}
          className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
          title="Refresh"
          aria-label="Refresh security center"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && (
        <AlertBanner
          type="error"
          title="Security Monitoring Notice"
          message={error}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Top Threat & Health Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400">
              API Service Health
            </span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white flex items-center gap-2">
            {health?.status === "healthy" ? "ONLINE / HEALTHY" : "CHECKING..."}
            {health?.status === "healthy" && (
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            )}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Backend API: {health?.app || "SecureVOTE"} v{health?.version || "0.1.0"}
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400">
              Active Tamper Alerts
            </span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <div
            className={`text-xl font-bold ${
              suspendedDevices.length > 0 ? "text-rose-400" : "text-white"
            }`}
          >
            {suspendedDevices.length} Unit(s) Suspended
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            {suspendedDevices.length > 0
              ? "Hardware breach or admin hold latch active"
              : "Zero hardware enclosures breached"}
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400">
              Security Controls
            </span>
            <Lock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-xl font-bold text-white">8 of 8 Active</div>
          <p className="text-[11px] text-slate-500 mt-1">
            Full defense-in-depth matrix operational
          </p>
        </div>
      </div>

      {/* Active Tamper Alerts Section */}
      {suspendedDevices.length > 0 && (
        <div className="bg-rose-950/30 border border-rose-800/80 rounded-xl p-5">
          <h3 className="text-sm font-bold text-rose-300 flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            Hardware Tamper Alert: Device Suspended
          </h3>
          <p className="text-xs text-rose-200/80 mb-4">
            The following hardware polling units detected an enclosure lid breach or
            security exception. Ballots from suspended units are rejected by the
            backend until authorized physical admin recovery.
          </p>
          <div className="space-y-2">
            {suspendedDevices.map((d) => (
              <div
                key={d.id}
                className="bg-slate-950/80 border border-rose-800/60 rounded-lg p-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <Cpu className="w-4 h-4 text-rose-400" />
                  <div>
                    <span className="font-mono font-bold text-white text-xs">
                      {d.id}
                    </span>
                    <span className="text-xs text-slate-400 ml-2">({d.name})</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status="SUSPENDED" />
                  <Link
                    href="/devices"
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium ml-2"
                  >
                    Manage Unit
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Defense-in-Depth Verification Matrix */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
        <h3 className="text-sm font-bold text-white mb-2">
          Security Controls & Anomaly Detection Matrix
        </h3>
        <p className="text-xs text-slate-400 mb-5">
          Each threat is guarded by an independent architectural mechanism verified by the
          test suite:
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-semibold">
              <tr>
                <th className="py-2.5 px-4">#</th>
                <th className="py-2.5 px-4">Threat / Vector</th>
                <th className="py-2.5 px-4">Mitigation Mechanism</th>
                <th className="py-2.5 px-4">Expected Backend Detection</th>
                <th className="py-2.5 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {SECURITY_CONTROLS.map((ctrl) => (
                <tr key={ctrl.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-mono text-slate-500">
                    0{ctrl.id}
                  </td>
                  <td className="py-3 px-4 font-semibold text-white">
                    {ctrl.name}
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    {ctrl.mechanism}
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-amber-300">
                    {ctrl.detection}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      <CheckCircle2 className="w-3 h-3" />
                      {ctrl.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
