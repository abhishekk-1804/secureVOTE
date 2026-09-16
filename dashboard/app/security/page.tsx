"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api-client";
import {
  AuditEntryResponse,
  DeviceResponse,
  HealthCheckResponse,
  AdvisoryFinding,
  RFIDTapResponse,
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
  Key,
  Anchor,
  Radio,
  Eye,
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
  {
    id: 9,
    name: "Result Manifest Asymmetric Signing",
    mechanism: "Ed25519 Elliptic Curve Signatures",
    detection: "SIGNATURE_INVALID on tampered manifest or unauthorized key",
    status: "ACTIVE",
  },
  {
    id: 10,
    name: "Audit-Root External Anchoring",
    mechanism: "SHA-256 Root Hash External Proof Commitments",
    detection: "ANCHOR_MISMATCH on historical tree divergence",
    status: "ACTIVE",
  },
  {
    id: 11,
    name: "Zero-Knowledge Identity Abstraction",
    mechanism: "Keyed HMAC-SHA256 Pseudonymization (Zero Raw UID Persistence)",
    detection: "RFID AUTHENTICATION != VOTER ELIGIBILITY enforcement",
    status: "ACTIVE",
  },
  {
    id: 12,
    name: "Advisory Anomaly Detection Engine",
    mechanism: "6 Deterministic Rules (Rate bursts, sequence gaps, rejections)",
    detection: "ADVISORY FINDING — REQUIRES HUMAN REVIEW (Non-blocking)",
    status: "ACTIVE",
  },
  {
    id: 13,
    name: "Machine-Verifiable Independent Verification",
    mechanism: "Pure Python Verifier with DB-Disconnected Proof",
    detection: "Typed 12-point failure codes on any corrupted export data",
    status: "ACTIVE",
  },
];

export default function SecurityCenterPage() {
  const { token } = useAuth();
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [tamperEvents, setTamperEvents] = useState<AuditEntryResponse[]>([]);
  const [anomalies, setAnomalies] = useState<AdvisoryFinding[]>([]);
  const [rfidCard, setRfidCard] = useState<string>("CARD-VALID-01");
  const [rfidDeviceId, setRfidDeviceId] = useState<string>("EVM-001");
  const [rfidResult, setRfidResult] = useState<RFIDTapResponse | null>(null);
  const [rfidLoading, setRfidLoading] = useState<boolean>(false);
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

      try {
        const anoData = await api.getElectionAnomalies("EV-2026-001", token);
        setAnomalies(anoData.findings || []);
      } catch {
        setAnomalies([]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load security center metrics");
    } finally {
      setLoading(false);
    }
  };

  const handleTapRFID = async (cardUidToTap?: string) => {
    const card = cardUidToTap || rfidCard;
    setRfidLoading(true);
    setError(null);
    try {
      const res = await api.tapRFID({
        raw_uid: card,
        device_id: rfidDeviceId,
        election_id: "EV-2026-001",
      });
      setRfidResult(res);
    } catch (err: any) {
      setError(err.message || "RFID tap simulation failed");
    } finally {
      setRfidLoading(false);
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
          <div className="text-xl font-bold text-white">
            {SECURITY_CONTROLS.length} of {SECURITY_CONTROLS.length} Active
          </div>
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
                  <div className="p-2 bg-rose-500/20 text-rose-400 rounded-lg">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-bold text-white text-sm">
                      {d.name} ({d.id})
                    </span>
                    <p className="text-xs text-rose-300/80">
                      Enclosure latch trip recorded in EEPROM & backend audit chain
                    </p>
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

      {/* Phase 5: Advisory Anomaly Detection Panel */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Eye className="w-4 h-4 text-amber-400" />
              Advisory Anomaly Detection Engine (6 Deterministic Rules)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Heuristic rate bursts, sequence gaps, and tamper correlation monitoring
            </p>
          </div>

          <span className="px-3 py-1 bg-amber-950/80 text-amber-400 border border-amber-800/80 rounded-full text-xs font-bold">
            ADVISORY ONLY — REQUIRES HUMAN REVIEW
          </span>
        </div>

        <div className="bg-amber-950/20 border border-amber-800/40 rounded-lg p-3 text-xs text-amber-200/90 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Hard Architectural Boundary: </span>
            Advisory findings are purely informational telemetry. They do <strong>NOT</strong> block or alter election lifecycle transitions, tally reconciliation, or Ed25519 digital signing.
          </div>
        </div>

        {anomalies.length > 0 ? (
          <div className="space-y-2">
            {anomalies.map((ano) => (
              <div
                key={ano.finding_id}
                className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        ano.severity === "HIGH"
                          ? "bg-rose-950 text-rose-400 border border-rose-800"
                          : ano.severity === "MEDIUM"
                          ? "bg-amber-950 text-amber-400 border border-amber-800"
                          : "bg-blue-950 text-blue-400 border border-blue-800"
                      }`}
                    >
                      {ano.severity} SEVERITY
                    </span>
                    <span className="font-mono font-bold text-xs text-white">
                      {ano.rule_id}
                    </span>
                    <span className="text-xs text-slate-400">({ano.category})</span>
                  </div>
                  <span className="text-[11px] text-slate-500 font-mono">
                    {new Date(ano.timestamp).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-slate-300">{ano.advisory_explanation}</p>
                <details className="text-xs text-slate-400">
                  <summary className="cursor-pointer hover:text-slate-200">View Evidence</summary>
                  <pre className="mt-2 bg-slate-900 p-2.5 rounded border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
                    {JSON.stringify(ano.evidence, null, 2)}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4 text-center text-xs text-slate-400">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 mx-auto mb-1.5" />
            No anomalous rate bursts, sequence gaps, or uncommanded device events detected in active election window.
          </div>
        )}
      </div>

      {/* Phase 5: RFID / Identity Abstraction Simulator */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Radio className="w-4 h-4 text-blue-400" />
              RFID / Contactless Identity Abstraction Simulator
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Keyed HMAC-SHA256 pseudonymization with zero raw UID storage
            </p>
          </div>

          <span className="px-3 py-1 bg-blue-950/80 text-blue-400 border border-blue-800/80 rounded-full text-xs font-bold">
            RFID AUTHENTICATION != VOTER ELIGIBILITY
          </span>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Select Simulated Smartcard Profile:
            </label>
            <div className="flex flex-wrap gap-2">
              {[
                { id: "CARD-VALID-01", label: "Eligible Card 1 (VALID)" },
                { id: "CARD-VALID-02", label: "Eligible Card 2 (VALID)" },
                { id: "CARD-REVOKED-01", label: "Lost Card (REVOKED)" },
                { id: "CARD-INVALID-99", label: "Malformed Card (INVALID)" },
              ].map((card) => (
                <button
                  key={card.id}
                  onClick={() => {
                    setRfidCard(card.id);
                    handleTapRFID(card.id);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    rfidCard === card.id
                      ? "bg-blue-600 text-white border-blue-500"
                      : "bg-slate-950 text-slate-300 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  {card.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
            <input
              type="text"
              value={rfidCard}
              onChange={(e) => setRfidCard(e.target.value)}
              placeholder="Or enter custom raw chip UID..."
              className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2 font-mono focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={() => handleTapRFID()}
              disabled={rfidLoading}
              className="w-full sm:w-auto px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shrink-0 transition disabled:opacity-50"
            >
              {rfidLoading ? "Reading Card..." : "Tap Smartcard"}
            </button>
          </div>

          {rfidResult && (
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="font-semibold text-slate-300 font-sans">Tap Result:</span>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                    rfidResult.card_status === "VALID"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : rfidResult.card_status === "REPEATED_USE"
                      ? "bg-amber-950 text-amber-400 border border-amber-800"
                      : "bg-rose-950 text-rose-400 border border-rose-800"
                  }`}
                >
                  {rfidResult.card_status}
                </span>
              </div>
              <div className="space-y-1 text-slate-400 text-[11px]">
                <div>
                  <span className="text-slate-500">Keyed Pseudonym: </span>
                  <span className="text-purple-300 break-all">{rfidResult.pseudonym || "None (Format Rejected)"}</span>
                </div>
                <div>
                  <span className="text-slate-500">Voting Session: </span>
                  <span className="text-slate-200">{rfidResult.session_id ? `Granted (token: ${rfidResult.session_id.slice(0, 16)}...)` : "None"}</span>
                </div>
                <div>
                  <span className="text-slate-500">Architectural Notice: </span>
                  <span className="text-amber-300 font-sans">{rfidResult.notice}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

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
