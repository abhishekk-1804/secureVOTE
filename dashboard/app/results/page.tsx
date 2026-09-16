"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api-client";
import { VerificationResponse, ElectionResponse } from "@/lib/types";
import { StatusBadge } from "@/components/common/StatusBadge";
import { AlertBanner } from "@/components/common/AlertBanner";
import {
  CheckCircle2,
  XCircle,
  ShieldCheck,
  FileCode,
  Scale,
  RefreshCw,
  Award,
  AlertTriangle,
} from "lucide-react";

export default function ResultsPage() {
  const { token, role } = useAuth();
  const [elections, setElections] = useState<ElectionResponse[]>([]);
  const [selectedElectionId, setSelectedElectionId] = useState<string>("EV-2026-001");
  const [results, setResults] = useState<VerificationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [verifyLoading, setVerifyLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showManifestJson, setShowManifestJson] = useState<boolean>(false);

  const fetchResults = async (electionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const all = await api.getElections(token);
      setElections(all);
      const target = all.find((e) => e.id === electionId) || all[0];
      if (target) {
        setSelectedElectionId(target.id);
        const res = await api.getResults(target.id, token);
        setResults(res);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load independent results");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults(selectedElectionId);
  }, [token]);

  const handleRunVerification = async () => {
    if (!token) return;
    if (role !== "ADMIN" && role !== "AUDITOR") {
      setError("Forbidden: Only ADMIN or AUDITOR roles can run formal verification.");
      return;
    }
    setVerifyLoading(true);
    setError(null);
    try {
      const res = await api.runVerification(selectedElectionId, token);
      setResults(res);
    } catch (err: any) {
      setError(err.message || "Independent verification execution failed");
    } finally {
      setVerifyLoading(false);
    }
  };

  const manifest = results?.manifest;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Results & Independent Verification
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographic tallies reconstructed from raw records with exact zero-drift reconciliation
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedElectionId}
            onChange={(e) => {
              setSelectedElectionId(e.target.value);
              fetchResults(e.target.value);
            }}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
          >
            {elections.map((el) => (
              <option key={el.id} value={el.id}>
                {el.id} — {el.title}
              </option>
            ))}
          </select>

          {(role === "ADMIN" || role === "AUDITOR") && (
            <button
              onClick={handleRunVerification}
              disabled={verifyLoading || loading}
              className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${verifyLoading ? "animate-spin" : ""}`}
              />
              Run Full Verification
            </button>
          )}

          <button
            onClick={() => fetchResults(selectedElectionId)}
            disabled={loading}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
            title="Refresh"
            aria-label="Refresh results"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <AlertBanner
          type="error"
          title="Verification Notice"
          message={error}
          onDismiss={() => setError(null)}
        />
      )}

      {results && (
        <>
          {/* Top Verification Summary Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
              <div>
                <span className="text-xs font-medium text-slate-400">
                  VERIFICATION STATUS
                </span>
                <div className="flex items-center gap-3 mt-1">
                  <h2 className="text-2xl font-bold text-white tracking-tight">
                    {results.overall_status === "PASSED"
                      ? "Independent Verification: PASSED"
                      : "Independent Verification: FAILED"}
                  </h2>
                  <StatusBadge status={results.overall_status} />
                </div>
              </div>

              {manifest && (
                <button
                  onClick={() => setShowManifestJson(!showManifestJson)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition"
                >
                  <FileCode className="w-3.5 h-3.5 text-blue-400" />
                  {showManifestJson ? "Hide Manifest JSON" : "View Signed Manifest"}
                </button>
              )}
            </div>

            {/* Verification Pillars 4-Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
              {/* 1. Configuration Hash */}
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300">
                    Configuration Hash
                  </span>
                  {results.config_hash_valid ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-500" />
                  )}
                </div>
                <div className="text-sm font-bold text-white">
                  {results.config_hash_valid ? "FROZEN & VALID" : "HASH MISMATCH"}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  SHA-256 of candidate slate
                </p>
              </div>

              {/* 2. Audit Chain */}
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300">
                    Audit Hash Chain
                  </span>
                  {results.audit_chain_intact ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-500" />
                  )}
                </div>
                <div className="text-sm font-bold text-white">
                  {results.audit_chain_intact ? "CHAIN INTACT" : "TAMPER DETECTED"}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Append-only cryptographic link
                </p>
              </div>

              {/* 3. Reconciliation */}
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300">
                    Exact Reconciliation
                  </span>
                  {results.reconciliation_passed ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-500" />
                  )}
                </div>
                <div className="text-sm font-bold text-white">
                  {results.reconciliation_passed ? "EXACT ZERO-DRIFT" : "DRIFT DETECTED"}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Zero tolerance cross-check
                </p>
              </div>

              {/* 4. Independent Tally */}
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300">
                    Independent Recount
                  </span>
                  {results.tally_independently_verified ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-500" />
                  )}
                </div>
                <div className="text-sm font-bold text-white">
                  {results.tally_independently_verified
                    ? "RECOUNT MATCHES"
                    : "TALLY MISMATCH"}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Recomputed from raw ballots
                </p>
              </div>
            </div>
          </div>

          {/* Signed Result Manifest Modal / Viewer */}
          {showManifestJson && manifest && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
              <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-blue-400" />
                Signed Result Manifest Document
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Manifest Hash:{" "}
                <span className="font-mono text-purple-300">{manifest.manifest_hash}</span>
              </p>
              <pre className="bg-slate-950 p-4 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto border border-slate-800">
                {JSON.stringify(manifest, null, 2)}
              </pre>
            </div>
          )}

          {/* Candidate Results Table & Progress Bars */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center justify-between">
              <span>Candidate Votes & Independent Tally</span>
              <span className="text-xs text-slate-400 font-normal">
                Total Ballots Counted: {manifest?.total_ballots ?? 0}
              </span>
            </h3>

            <div className="space-y-4">
              {manifest?.candidate_results.map((c) => (
                <div
                  key={c.candidate_id}
                  className="bg-slate-950 border border-slate-800/80 rounded-lg p-4"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2.5">
                      <span className="w-6 h-6 rounded bg-slate-800 text-blue-400 font-bold font-mono text-xs flex items-center justify-center">
                        {c.symbol || "?"}
                      </span>
                      <div>
                        <span className="font-semibold text-white text-sm mr-2">
                          {c.candidate_name}
                        </span>
                        <span className="text-xs text-slate-400">
                          ({c.party || "Independent"})
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-base font-bold text-white">
                        {c.vote_count} votes
                      </span>
                      <span className="text-xs text-slate-400 ml-2">
                        ({c.percentage.toFixed(2)}%)
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(c.percentage, 1)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Exact Reconciliation Breakdown Card */}
          {manifest?.reconciliation && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
              <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                <Scale className="w-4 h-4 text-emerald-400" />
                Reconciliation Breakdown (Zero Tolerance Discipline)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block text-[11px]">
                    Total Ballots in DB:
                  </span>
                  <span className="text-lg font-bold text-white">
                    {manifest.reconciliation.total_ballots}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block text-[11px]">
                    Sum of Candidate Totals:
                  </span>
                  <span className="text-lg font-bold text-white">
                    {manifest.reconciliation.sum_candidate_totals}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block text-[11px]">
                    Sum of Device Counters:
                  </span>
                  <span className="text-lg font-bold text-white">
                    {manifest.reconciliation.sum_device_totals}
                  </span>
                </div>
              </div>
              <div className="mt-4 text-xs text-slate-400 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <span className="font-semibold text-slate-300">
                  Mathematical Identity:{" "}
                </span>
                <code>
                  sum(candidates) [{manifest.reconciliation.sum_candidate_totals}] ==
                  total_ballots [{manifest.reconciliation.total_ballots}] ==
                  sum(devices) [{manifest.reconciliation.sum_device_totals}]
                </code>
                <div className="mt-1 flex items-center gap-2">
                  <span>Delta:</span>
                  <span
                    className={
                      manifest.reconciliation.is_exact_match
                        ? "text-emerald-400 font-bold"
                        : "text-rose-400 font-bold"
                    }
                  >
                    0 (Exact match)
                  </span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
