"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api-client";
import { ElectionResponse, ElectionState } from "@/lib/types";
import { StatusBadge } from "@/components/common/StatusBadge";
import { AlertBanner } from "@/components/common/AlertBanner";
import {
  Vote,
  Cpu,
  Lock,
  Play,
  Square,
  Share2,
  AlertOctagon,
  Hash,
  Clock,
  RefreshCw,
  Layers,
  ArrowUpRight,
  CheckCircle2,
} from "lucide-react";

interface ElectionLifecycleStage {
  step: number;
  title: string;
  eciRef: string;
  description: string;
  href: string;
  isCurrent: (state: ElectionState) => boolean;
  isDone: (state: ElectionState) => boolean;
}

const LIFECYCLE_STAGES: ElectionLifecycleStage[] = [
  {
    step: 1,
    title: "Setup & Gazette Notification",
    eciRef: "RP Act 1951 § 30",
    description: "Constituency setup, electoral roll definition, polling timetable.",
    href: "/election/setup",
    isCurrent: (s) => s === "CONFIGURED",
    isDone: (s) => s !== "CONFIGURED",
  },
  {
    step: 2,
    title: "Candidate Roster (Form 7A)",
    eciRef: "Rule 10(1) CE Rules",
    description: "Nomination scrutiny, symbol allotment, candidate slate freeze.",
    href: "/election/candidates",
    isCurrent: (s) => s === "CONFIGURED",
    isDone: (s) => s !== "CONFIGURED",
  },
  {
    step: 3,
    title: "Station Allocation & BLO Prep",
    eciRef: "Handbook RO Ch. 2",
    description: "Polling station layout, Booth Level Officer assignment, voter queue plans.",
    href: "/election/polling-stations",
    isCurrent: (s) => s === "LOCKED",
    isDone: (s) => ["OPEN", "SUSPENDED", "CLOSED", "PUBLISHED"].includes(s),
  },
  {
    step: 4,
    title: "FLC & Hardware Commissioning",
    eciRef: "EVM Manual Ch. 3",
    description: "First Level Checking, pink paper seal validation, diagnostic self-test.",
    href: "/election/devices",
    isCurrent: (s) => s === "LOCKED",
    isDone: (s) => ["OPEN", "SUSPENDED", "CLOSED", "PUBLISHED"].includes(s),
  },
  {
    step: 5,
    title: "Pre-Poll Mock Poll & Clear",
    eciRef: "Rule 49E CE Rules",
    description: "Mandatory 50+ mock votes in presence of polling agents, CLR button verification.",
    href: "/evm",
    isCurrent: (s) => s === "LOCKED",
    isDone: (s) => ["OPEN", "SUSPENDED", "CLOSED", "PUBLISHED"].includes(s),
  },
  {
    step: 6,
    title: "Poll Commencement (07:00 HRS)",
    eciRef: "Rule 49J CE Rules",
    description: "Presiding Officer diary initialized, green paper seal verification.",
    href: "/command",
    isCurrent: (s) => s === "OPEN",
    isDone: (s) => ["CLOSED", "PUBLISHED"].includes(s),
  },
  {
    step: 7,
    title: "Poll-Day Turnout & Monitoring",
    eciRef: "ECI Turnout App",
    description: "Two-hourly voter turnout metrics, incident logging, webcasting oversight.",
    href: "/election/polling",
    isCurrent: (s) => s === "OPEN" || s === "SUSPENDED",
    isDone: (s) => ["CLOSED", "PUBLISHED"].includes(s),
  },
  {
    step: 8,
    title: "Poll Close & Form 17C Part I",
    eciRef: "Rule 49S CE Rules",
    description: "CU close button pressed, total votes sealed with special address tags.",
    href: "/command",
    isCurrent: (s) => s === "CLOSED",
    isDone: (s) => s === "CLOSED" || s === "PUBLISHED",
  },
  {
    step: 9,
    title: "Strongroom Custody & Transit",
    eciRef: "EVM Manual Ch. 8",
    description: "Double-lock strongroom entry, continuous CCTV audit log, security patrol.",
    href: "/election/audit",
    isCurrent: (s) => s === "CLOSED",
    isDone: (s) => s === "PUBLISHED",
  },
  {
    step: 10,
    title: "Counting Center Operations",
    eciRef: "Rule 56D CE Rules",
    description: "Round-wise CU tallying, RO & candidate counting agent cross-checks.",
    href: "/election/counting",
    isCurrent: (s) => s === "CLOSED",
    isDone: (s) => s === "PUBLISHED",
  },
  {
    step: 11,
    title: "Mandatory VVPAT & Crypto Audit",
    eciRef: "SC 2019 Precedent / Research",
    description: "Indian practice: 5 random PS VVPAT paper counts. Prototype: Independent hash-chain verification.",
    href: "/election/verification",
    isCurrent: (s) => s === "PUBLISHED",
    isDone: (s) => s === "PUBLISHED",
  },
  {
    step: 12,
    title: "Result Declaration (Form 20/21E)",
    eciRef: "Rule 64 CE Rules",
    description: "Official result manifest publishing, public gazette notification.",
    href: "/election/results",
    isCurrent: (s) => s === "PUBLISHED",
    isDone: (s) => s === "PUBLISHED",
  },
];

export default function CommandCenterPage() {
  const { token, role } = useAuth();
  const [elections, setElections] = useState<ElectionResponse[]>([]);
  const [selectedElectionId, setSelectedElectionId] = useState<string>("EV-2026-001");
  const [election, setElection] = useState<ElectionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchElectionData = async (electionId: string) => {
    setLoading(true);
    setError(null);
    try {
      let all: ElectionResponse[] = [];
      try {
        const res = await api.getElections(token);
        all = Array.isArray(res) ? res : ((res as any)?.elections || []);
      } catch {
        // Fallback to public transparency overview if officer election list fails
        const publicList = await api.getTransparencyElections().catch(() => []);
        all = (Array.isArray(publicList) ? publicList : []).map((t) => ({
          id: t.election_id,
          title: t.election_name || t.election_id,
          name: t.election_name,
          description: "Simulated General Election",
          state: (t.state as ElectionState) || "OPEN",
          configuration_hash: null,
          device_count: t.device_count || 0,
          ballot_count: t.total_ballots || 0,
          created_at: new Date().toISOString(),
          opened_at: null,
          closed_at: null,
          published_at: null,
          candidates: [],
        }));
      }

      if (!Array.isArray(all) || all.length === 0) {
        all = [
          {
            id: "EV-2026-001",
            title: "General Election 2026",
            name: "General Election 2026",
            description: "Simulated General Election",
            state: "OPEN",
            configuration_hash: null,
            device_count: 3,
            ballot_count: 0,
            created_at: new Date().toISOString(),
            opened_at: null,
            closed_at: null,
            published_at: null,
            candidates: [],
          },
        ];
      }

      setElections(all);
      const target = all.find((e) => e.id === electionId) || all[0];
      if (target) {
        setSelectedElectionId(target.id);
        try {
          const detailed = await api.getElection(target.id, token);
          setElection(detailed);
        } catch {
          setElection(target);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load election data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchElectionData(selectedElectionId);
  }, [token]);

  const handleStateTransition = async (newState: ElectionState) => {
    if (!election || !token) return;
    if (role !== "ADMIN") {
      setError("Forbidden: Only ADMIN users may transition election state.");
      return;
    }
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await api.updateElectionState(election.id, newState, token);
      setElection(updated);
      setSuccessMsg(`Election state successfully changed to ${newState}`);
      // Refresh list
      const all = await api.getElections(token);
      setElections(Array.isArray(all) ? all : []);
    } catch (err: any) {
      setError(err.message || `Failed to transition state to ${newState}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Bar: Selector & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Election Command Center
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage lifecycle, candidate freezing, and hardware device states
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedElectionId}
            onChange={(e) => {
              setSelectedElectionId(e.target.value);
              fetchElectionData(e.target.value);
            }}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
          >
            {(Array.isArray(elections) ? elections : []).map((el) => (
              <option key={el.id} value={el.id}>
                {el.id}  -  {el.name || (el as any).title || el.id}
              </option>
            ))}
          </select>
          <button
            onClick={() => fetchElectionData(selectedElectionId)}
            disabled={loading}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
            title="Refresh"
            aria-label="Refresh data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <AlertBanner
          type="error"
          title="Operation Error"
          message={error}
          onDismiss={() => setError(null)}
        />
      )}

      {successMsg && (
        <AlertBanner
          type="success"
          title="State Updated"
          message={successMsg}
          onDismiss={() => setSuccessMsg(null)}
        />
      )}

      {election && (
        <>
          {/* Main Info Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-sm font-semibold text-blue-400 font-mono">
                    {election.id}
                  </span>
                  <StatusBadge status={election.state} />
                </div>
                <h2 className="text-2xl font-bold text-white">
                  {election.title}
                </h2>
                {election.description && (
                  <p className="text-xs text-slate-400 mt-1">
                    {election.description}
                  </p>
                )}
              </div>

              {/* Lifecycle Actions */}
              <div className="flex flex-wrap items-center gap-2">
                {role !== "ADMIN" && (
                  <span className="text-xs text-slate-500 italic mr-2">
                    Read-only mode ({role})
                  </span>
                )}

                {election.state === "CONFIGURED" && (
                  <button
                    disabled={role !== "ADMIN" || actionLoading}
                    onClick={() => handleStateTransition("LOCKED")}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Lock className="w-3.5 h-3.5" />
                    Lock Configuration
                  </button>
                )}

                {election.state === "LOCKED" && (
                  <button
                    disabled={role !== "ADMIN" || actionLoading}
                    onClick={() => handleStateTransition("OPEN")}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Play className="w-3.5 h-3.5" />
                    Open Polls
                  </button>
                )}

                {election.state === "OPEN" && (
                  <>
                    <button
                      disabled={role !== "ADMIN" || actionLoading}
                      onClick={() => handleStateTransition("SUSPENDED")}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <AlertOctagon className="w-3.5 h-3.5" />
                      Suspend Polls
                    </button>
                    <button
                      disabled={role !== "ADMIN" || actionLoading}
                      onClick={() => handleStateTransition("CLOSED")}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Square className="w-3.5 h-3.5" />
                      Close Polls
                    </button>
                  </>
                )}

                {election.state === "SUSPENDED" && (
                  <>
                    <button
                      disabled={role !== "ADMIN" || actionLoading}
                      onClick={() => handleStateTransition("OPEN")}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Resume Polls
                    </button>
                    <button
                      disabled={role !== "ADMIN" || actionLoading}
                      onClick={() => handleStateTransition("CLOSED")}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Square className="w-3.5 h-3.5" />
                      Close Polls
                    </button>
                  </>
                )}

                {election.state === "CLOSED" && (
                  <button
                    disabled={role !== "ADMIN" || actionLoading}
                    onClick={() => handleStateTransition("PUBLISHED")}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Share2 className="w-3.5 h-3.5" />
                    Publish Results
                  </button>
                )}
              </div>
            </div>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between text-slate-400 mb-1">
                  <span className="text-xs font-medium">Total Ballots Cast</span>
                  <Vote className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {election.ballot_count}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">Recorded ballots</p>
              </div>

              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between text-slate-400 mb-1">
                  <span className="text-xs font-medium">Hardware Units</span>
                  <Cpu className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {election.device_count}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">Active polling units</p>
              </div>

              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between text-slate-400 mb-1">
                  <span className="text-xs font-medium">Config Hash</span>
                  <Hash className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-xs font-mono font-semibold text-slate-200 truncate mt-1">
                  {election.configuration_hash ? (
                    <span title={election.configuration_hash}>
                      {election.configuration_hash.substring(0, 16)}...
                    </span>
                  ) : (
                    <span className="text-slate-500">Not frozen yet</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  SHA-256 candidates fingerprint
                </p>
              </div>

              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between text-slate-400 mb-1">
                  <span className="text-xs font-medium">Timeline</span>
                  <Clock className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-xs text-slate-200 mt-1">
                  {election.opened_at ? (
                    <span>
                      Opened: {new Date(election.opened_at).toLocaleTimeString()}
                    </span>
                  ) : (
                    <span className="text-slate-500">Not opened</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  {election.closed_at
                    ? `Closed: ${new Date(election.closed_at).toLocaleTimeString()}`
                    : "Voting active / pending"}
                </p>
              </div>
            </div>
          </div>

          {/* 12-Stage Operational Lifecycle */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-400">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    12-Stage Indian Election Operational Lifecycle
                  </h3>
                  <p className="text-xs text-slate-400">
                    Procedural workflow grounded in Conduct of Elections Rules 1961 &amp; ECI Handbooks
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded font-mono text-[11px] font-semibold">
                  SIMULATION ENVIRONMENT
                </span>
                <span className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded font-mono text-[11px]">
                  STATE: {election.state}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {LIFECYCLE_STAGES.map((st) => {
                const isCurrent = st.isCurrent(election.state);
                const isDone = st.isDone(election.state);
                return (
                  <Link
                    key={st.step}
                    href={st.href}
                    className={`group relative p-3.5 rounded-lg border transition flex flex-col justify-between ${
                      isCurrent
                        ? "bg-blue-950/30 border-blue-500/60 shadow-sm shadow-blue-900/20 hover:border-blue-400"
                        : isDone
                        ? "bg-slate-950/70 border-emerald-500/30 hover:border-emerald-500/60"
                        : "bg-slate-950/40 border-slate-800/80 opacity-70 hover:opacity-100 hover:border-slate-700"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs font-bold text-slate-400">
                          STAGE {st.step.toString().padStart(2, "0")}
                        </span>
                        {isDone ? (
                          <span className="flex items-center gap-1 text-[10px] font-mono font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                            <CheckCircle2 className="w-3 h-3" /> DONE
                          </span>
                        ) : isCurrent ? (
                          <span className="text-[10px] font-mono font-bold text-blue-400 bg-blue-500/20 px-2 py-0.5 rounded border border-blue-500/40 animate-pulse">
                            ACTIVE
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                            UPCOMING
                          </span>
                        )}
                      </div>
                      <h4 className="text-xs font-bold text-white group-hover:text-blue-300 transition-colors">
                        {st.title}
                      </h4>
                      <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                        {st.eciRef}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
                        {st.description}
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-blue-400 font-medium">
                      <span>Open console</span>
                      <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Candidate List Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center justify-between">
              <span>Candidate Roster ({election.candidates.length})</span>
              <span className="text-xs font-normal text-slate-400">
                Frozen upon locking
              </span>
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Pos</th>
                    <th className="py-2.5 px-4">ID</th>
                    <th className="py-2.5 px-4">Name</th>
                    <th className="py-2.5 px-4">Party Affiliation</th>
                    <th className="py-2.5 px-4 text-center">Symbol</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {election.candidates.map((cand) => (
                    <tr
                      key={cand.id}
                      className="hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-3 px-4 font-mono text-slate-400">
                        #{cand.position}
                      </td>
                      <td className="py-3 px-4 font-mono font-medium text-blue-400">
                        {cand.id}
                      </td>
                      <td className="py-3 px-4 font-semibold text-white">
                        {cand.name}
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {cand.party || " - "}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-block px-2 py-0.5 bg-slate-800 text-blue-400 rounded font-bold font-mono">
                          {cand.symbol || " - "}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
