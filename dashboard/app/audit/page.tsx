"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, isDemoMode } from "@/lib/api-client";
import {
  AuditEntryResponse,
  AuditVerificationResponse,
  ElectionResponse,
} from "@/lib/types";
import { StatusBadge } from "@/components/common/StatusBadge";
import { AlertBanner } from "@/components/common/AlertBanner";
import {
  ScrollText,
  ShieldCheck,
  Filter,
  RefreshCw,
  Link as LinkIcon,
  CheckCircle2,
  XCircle,
  Tag,
} from "lucide-react";

export default function AuditExplorerPage() {
  const { token } = useAuth();
  const [elections, setElections] = useState<ElectionResponse[]>([]);
  const [selectedElectionId, setSelectedElectionId] = useState<string>("EV-2026-001");
  const [entries, setEntries] = useState<AuditEntryResponse[]>([]);
  const [verification, setVerification] = useState<AuditVerificationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [verifyLoading, setVerifyLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [filterDemoOnly, setFilterDemoOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");

  const fetchAuditData = async (electionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const all = await api.getElections(token);
      setElections(all);
      const target = all.find((e) => e.id === electionId) || all[0];
      if (target) {
        setSelectedElectionId(target.id);
        const [auditLog, chainStatus] = await Promise.all([
          api.getAuditLog(target.id, token),
          api.verifyAuditChain(target.id, token),
        ]);
        setEntries(auditLog);
        setVerification(chainStatus);
      }
    } catch (err: any) {
      setError(err.message || "Failed to fetch audit log");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData(selectedElectionId);
  }, [token]);

  const handleVerifyChain = async () => {
    setVerifyLoading(true);
    setError(null);
    try {
      const status = await api.verifyAuditChain(selectedElectionId, token);
      setVerification(status);
    } catch (err: any) {
      setError(err.message || "Verification request failed");
    } finally {
      setVerifyLoading(false);
    }
  };

  const eventTypes = ["ALL", ...Array.from(new Set(entries.map((e) => e.event_type)))];

  const filteredEntries = entries.filter((entry) => {
    if (selectedType !== "ALL" && entry.event_type !== selectedType) {
      return false;
    }
    const isDemo = isDemoMode(entry);
    if (filterDemoOnly && !isDemo) {
      return false;
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchActor = entry.actor?.toLowerCase().includes(q);
      const matchDevice = entry.device_id?.toLowerCase().includes(q);
      const matchType = entry.event_type.toLowerCase().includes(q);
      const matchData = entry.event_data?.toLowerCase().includes(q);
      return matchActor || matchDevice || matchType || matchData;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Append-Only Audit Explorer
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographic SHA-256 hash-chained immutable event timeline
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedElectionId}
            onChange={(e) => {
              setSelectedElectionId(e.target.value);
              fetchAuditData(e.target.value);
            }}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
          >
            {elections.map((el) => (
              <option key={el.id} value={el.id}>
                {el.id} — {el.title}
              </option>
            ))}
          </select>

          <button
            onClick={handleVerifyChain}
            disabled={verifyLoading || loading}
            className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50"
          >
            <ShieldCheck
              className={`w-3.5 h-3.5 ${verifyLoading ? "animate-spin" : ""}`}
            />
            Verify Hash Chain
          </button>

          <button
            onClick={() => fetchAuditData(selectedElectionId)}
            disabled={loading}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
            title="Refresh"
            aria-label="Refresh audit log"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <AlertBanner
          type="error"
          title="Audit Service Notice"
          message={error}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Verification Status Banner */}
      {verification && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center gap-3">
            {verification.is_intact ? (
              <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg">
                <CheckCircle2 className="w-5 h-5" />
              </div>
            ) : (
              <div className="p-2 bg-rose-500/20 text-rose-400 rounded-lg">
                <XCircle className="w-5 h-5" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">
                  {verification.is_intact
                    ? "Cryptographic Chain Intact"
                    : "Cryptographic Chain Broken"}
                </span>
                <StatusBadge
                  status={verification.is_intact ? "INTACT" : "BROKEN"}
                />
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {verification.details}
              </p>
            </div>
          </div>
          <div className="text-xs text-slate-400 font-mono sm:text-right">
            <span>Total Verified Entries: </span>
            <span className="font-bold text-white">
              {verification.total_entries}
            </span>
          </div>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs font-semibold text-slate-300">Type:</span>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none"
            >
              {eventTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700">
            <input
              type="checkbox"
              checked={filterDemoOnly}
              onChange={(e) => setFilterDemoOnly(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
            />
            <span>Only [DEMO-MODE]</span>
          </label>
        </div>

        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by actor, device, data..."
          className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500 w-full sm:w-64"
        />
      </div>

      {/* Audit Log Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4">Seq</th>
                <th className="py-3 px-4">Event Type</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Device</th>
                <th className="py-3 px-4">Hash Chain (Prev → Entry)</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredEntries.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="py-8 text-center text-slate-500 font-sans text-xs"
                  >
                    No audit records matching selected criteria.
                  </td>
                </tr>
              ) : (
                filteredEntries.map((entry) => {
                  const isDemo = isDemoMode(entry);
                  return (
                    <tr
                      key={entry.id}
                      className="hover:bg-slate-800/40 transition-colors font-sans"
                    >
                      <td className="py-3 px-4 font-mono text-blue-400 font-medium">
                        #{entry.sequence_number}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-white font-mono text-[11px]">
                            {entry.event_type}
                          </span>
                          {isDemo && (
                            <span
                              data-testid="demo-mode-badge"
                              className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-400"
                            >
                              [DEMO-MODE]
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">
                        {entry.actor || "system"}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                        {entry.device_id || "—"}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px]">
                        <div className="flex items-center gap-1 text-slate-400">
                          <span
                            className="text-slate-500"
                            title={entry.previous_hash || "GENESIS"}
                          >
                            {entry.previous_hash
                              ? entry.previous_hash.substring(0, 8)
                              : "00000000"}
                          </span>
                          <LinkIcon className="w-3 h-3 text-slate-600" />
                          <span
                            className="text-purple-300 font-semibold"
                            title={entry.entry_hash}
                          >
                            {entry.entry_hash.substring(0, 8)}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="py-3 px-4">
                        {entry.event_data ? (
                          <span
                            className="font-mono text-[10px] text-slate-400 truncate max-w-xs block"
                            title={entry.event_data}
                          >
                            {entry.event_data}
                          </span>
                        ) : (
                          <span className="text-slate-600 text-[11px]">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
