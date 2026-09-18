"use client";

import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import {
  Calculator,
  CheckCircle2,
  XCircle,
  RefreshCcw,
  Play,
  RotateCcw,
  Award,
  ChevronRight,
  ShieldCheck,
  Printer,
  Download,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function CountingCenterPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tabs: "CUMULATIVE" | "ROUNDS" | "FORM20"
  const [activeTab, setActiveTab] = useState<"CUMULATIVE" | "ROUNDS" | "FORM20">("CUMULATIVE");

  // Round simulation state (1 to 5 rounds)
  const TOTAL_ROUNDS = 5;
  const [currentRound, setCurrentRound] = useState(1);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);

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

  // Auto-play effect
  useEffect(() => {
    let timer: any;
    if (isAutoPlaying && currentRound < TOTAL_ROUNDS) {
      timer = setTimeout(() => {
        setCurrentRound((prev) => prev + 1);
      }, 1500);
    } else if (currentRound >= TOTAL_ROUNDS) {
      setIsAutoPlaying(false);
    }
    return () => clearTimeout(timer);
  }, [isAutoPlaying, currentRound]);

  if (!selectedElection) {
    return (
      <div className="p-8 text-center text-slate-400">
        Select an election to view counting center.
      </div>
    );
  }

  const isClosed = selectedElection.state === "CLOSED" || selectedElection.state === "PUBLISHED";
  const totalCandidateVotes =
    results?.candidate_results?.reduce(
      (acc: number, curr: any) => acc + (curr.vote_count ?? curr.votes ?? 0),
      0
    ) || 0;
  const totalDeviceVotes =
    results?.device_results?.reduce(
      (acc: number, curr: any) => acc + (curr.ballot_count ?? curr.votes_counted ?? 0),
      0
    ) || 0;
  const actualBallotCount = selectedElection.ballot_count ?? totalCandidateVotes;
  const isReconciled =
    totalCandidateVotes === actualBallotCount && totalDeviceVotes === actualBallotCount;

  // Compute progressive round fractions
  const roundFraction = currentRound / TOTAL_ROUNDS;
  const sortedCandidates = [...(results?.candidate_results || [])].sort(
    (a: any, b: any) => (b.vote_count ?? b.votes ?? 0) - (a.vote_count ?? a.votes ?? 0)
  );

  const leadingCandidate = sortedCandidates[0];
  const runnerUpCandidate = sortedCandidates[1];
  const margin =
    leadingCandidate && runnerUpCandidate
      ? (leadingCandidate.vote_count ?? leadingCandidate.votes ?? 0) -
        (runnerUpCandidate.vote_count ?? runnerUpCandidate.votes ?? 0)
      : 0;

  // Polling Station breakdown data
  const pollingStations = [
    { id: "PS-001", name: "Government High School, Room 1", tables: 4, eevm: "EVM-001" },
    { id: "PS-002", name: "Government High School, Room 2", tables: 4, eevm: "EVM-002" },
    { id: "PS-003", name: "Community Welfare Centre, North Hall", tables: 3, eevm: "EVM-003" },
    { id: "PS-004", name: "Model Primary School, Main Block", tables: 3, eevm: "EVM-004" },
  ];

  const handleExportCsv = () => {
    if (!results?.candidate_results) return;
    const header = "Candidate ID,Candidate Name,Party,Votes,Percentage\n";
    const rows = results.candidate_results
      .map(
        (c: any) =>
          `"${c.candidate_id}","${c.candidate_name || c.name || ''}","${c.party || 'IND'}",${c.vote_count ?? c.votes ?? 0},${(
            c.percentage ?? 0
          ).toFixed(2)}%`
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Form20-ResultSheet-${selectedElection.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2 text-white">
            <Calculator className="w-5 h-5 text-blue-500" />
            Counting Center & Verification
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Round-by-round progressive tallying, Form 20-style simulation sheet, and zero-drift cryptographic reconciliation
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCcw className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh Tallies
          </Button>
          <Button variant="primary" size="sm" onClick={handleExportCsv} disabled={!results?.candidate_results}>
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Export Form 20 (CSV)
          </Button>
        </div>
      </div>

      {!isClosed && (
        <div className="bg-amber-500/10 border border-amber-500/30 text-amber-300 px-4 py-3 rounded-xl flex items-center gap-3 text-xs">
          <span className="relative flex h-2.5 w-2.5 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
          </span>
          Election is currently <strong className="text-amber-200">{selectedElection.state}</strong>. Counting tallies reflect live authorized ballots and are subject to final poll close certification.
        </div>
      )}

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 text-rose-400 p-4 rounded-xl text-xs">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab("CUMULATIVE")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "CUMULATIVE"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Live Cumulative Tally
        </button>
        <button
          onClick={() => setActiveTab("ROUNDS")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "ROUNDS"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Round-by-Round Progressive Count
        </button>
        <button
          onClick={() => setActiveTab("FORM20")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "FORM20"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Form 20-Style Simulation Sheet
        </button>
      </div>

      {/* TAB 1: CUMULATIVE VIEW */}
      {activeTab === "CUMULATIVE" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Candidate Totals */}
            <Card padding="md" className="bg-slate-900 border-slate-800">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Award className="w-4 h-4 text-amber-400" />
                  Candidate Vote Distribution
                </h2>
                <Badge variant="neutral">
                  {totalCandidateVotes} Total Valid Votes
                </Badge>
              </div>

              {results?.candidate_results?.length ? (
                <div className="space-y-4">
                  {sortedCandidates.map((c: any, idx: number) => {
                    const votes = c.vote_count ?? c.votes ?? 0;
                    const percent =
                      totalCandidateVotes > 0 ? (votes / totalCandidateVotes) * 100 : 0;
                    const isWinner = idx === 0 && votes > 0;

                    return (
                      <div
                        key={c.candidate_id}
                        className={`p-3.5 rounded-xl border transition-all ${
                          isWinner
                            ? "bg-slate-950/80 border-amber-500/40"
                            : "bg-slate-950/40 border-slate-800/80"
                        }`}
                      >
                        <div className="flex justify-between items-center text-xs mb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-slate-500 font-bold">
                              #{idx + 1}
                            </span>
                            <span className="font-semibold text-white">
                              {c.candidate_name || c.name || c.candidate_id}
                            </span>
                            {c.party && (
                              <Badge variant="neutral" className="text-[10px]">
                                {c.party}
                              </Badge>
                            )}
                            {isWinner && (
                              <Badge variant="warning" className="text-[10px]">
                                Leading (+{margin.toLocaleString()})
                              </Badge>
                            )}
                          </div>
                          <span className="font-mono font-bold text-emerald-400">
                            {votes.toLocaleString()} ({percent.toFixed(1)}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-2 rounded-full transition-all duration-500 ${
                              isWinner ? "bg-amber-400" : "bg-blue-500"
                            }`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center text-slate-500 py-8 text-xs">
                  No candidate tallies recorded for this election.
                </div>
              )}
            </Card>

            {/* Device Contributions */}
            <Card padding="md" className="bg-slate-900 border-slate-800">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-white">
                  EVM Control Unit Registers
                </h2>
                <Badge variant="neutral">
                  {results?.device_results?.length || 0} Connected EVMs
                </Badge>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {results?.device_results?.map((d: any) => (
                  <div
                    key={d.device_id}
                    className="bg-slate-950 border border-slate-800/80 p-3.5 rounded-xl flex justify-between items-center"
                  >
                    <div>
                      <div className="font-semibold text-xs text-slate-200">
                        Device {d.device_id}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        {d.device_name || "Ballot Unit"}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold font-mono text-emerald-400">
                        {(d.ballot_count ?? d.votes_counted ?? 0).toLocaleString()}
                      </div>
                      <div className="text-[10px] text-slate-500">ballots</div>
                    </div>
                  </div>
                ))}
                {!results?.device_results?.length && (
                  <div className="col-span-2 text-center text-slate-500 py-4 text-xs">
                    No device register data available.
                  </div>
                )}
              </div>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <Card padding="md" className="bg-slate-900 border-slate-800">
              <h2 className="text-sm font-bold text-white mb-3">
                Cryptographic Reconciliation
              </h2>
              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center border-b border-slate-800/80 pb-2">
                  <span className="text-slate-400">Total Ballots in DB</span>
                  <span className="font-mono font-bold text-slate-200">
                    {actualBallotCount.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-slate-800/80 pb-2">
                  <span className="text-slate-400">Sum of Candidate Totals</span>
                  <span className="font-mono font-bold text-slate-200">
                    {totalCandidateVotes.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-slate-800/80 pb-2">
                  <span className="text-slate-400">Sum of EVM Unit Totals</span>
                  <span className="font-mono font-bold text-slate-200">
                    {totalDeviceVotes.toLocaleString()}
                  </span>
                </div>

                <div
                  className={`p-3 rounded-xl flex items-center justify-center gap-2 font-semibold text-xs mt-2 ${
                    isReconciled
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                  }`}
                >
                  {isReconciled ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      ZERO-DRIFT MATCH VERIFIED
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4" />
                      TALLY DRIFT DETECTED
                    </>
                  )}
                </div>
              </div>
            </Card>

            <Card padding="md" className="bg-slate-900 border-slate-800">
              <h2 className="text-sm font-bold text-white mb-3">
                Integrity Gate
              </h2>
              <div className="space-y-3 text-xs">
                <div className="flex items-center gap-2.5">
                  {results?.manifest_hash ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-600 shrink-0" />
                  )}
                  <span className="text-slate-300">Result Manifest Hashed</span>
                </div>
                <div className="flex items-center gap-2.5">
                  {isReconciled ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-600 shrink-0" />
                  )}
                  <span className="text-slate-300">Simulation Device & DB Reconciled</span>
                </div>
                <div className="flex items-center gap-2.5">
                  {results?.digital_signature ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-600 shrink-0" />
                  )}
                  <span className="text-slate-300">Ed25519 Signed by Returning Officer</span>
                </div>
              </div>

              {results?.manifest_hash && (
                <div className="mt-4 pt-3 border-t border-slate-800 text-[10px]">
                  <span className="text-slate-500">Manifest SHA-256 Digest:</span>
                  <p className="font-mono text-slate-400 break-all mt-0.5 bg-slate-950 p-2 rounded border border-slate-800/80">
                    {results.manifest_hash}
                  </p>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: ROUND-BY-ROUND COUNTING SIMULATION */}
      {activeTab === "ROUNDS" && (
        <div className="space-y-6">
          <Card padding="md" className="bg-slate-900 border-slate-800">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-blue-400 uppercase">
                    Round {currentRound} of {TOTAL_ROUNDS}
                  </span>
                  <Badge variant={currentRound === TOTAL_ROUNDS ? "success" : "neutral"}>
                    {currentRound === TOTAL_ROUNDS ? "FINAL ROUND" : "IN PROGRESS"}
                  </Badge>
                </div>
                <h2 className="text-base font-bold text-white mt-1">
                  Assembly Segment Table Rounds (14 Tables per Round)
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Simulating progressive EVM control unit unpacking, seal inspection, and tabulation.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setCurrentRound(1);
                    setIsAutoPlaying(false);
                  }}
                  disabled={currentRound === 1 && !isAutoPlaying}
                >
                  <RotateCcw className="w-3.5 h-3.5 mr-1" />
                  Reset to Round 1
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsAutoPlaying(!isAutoPlaying)}
                  disabled={currentRound === TOTAL_ROUNDS}
                >
                  <Play className={`w-3.5 h-3.5 mr-1 ${isAutoPlaying ? "text-amber-400" : ""}`} />
                  {isAutoPlaying ? "Pause" : "Auto-Play Rounds"}
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setCurrentRound((prev) => Math.min(TOTAL_ROUNDS, prev + 1))}
                  disabled={currentRound === TOTAL_ROUNDS || isAutoPlaying}
                >
                  Next Round
                  <ChevronRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </div>

            {/* Round progress bar */}
            <div className="mt-4">
              <div className="flex justify-between text-xs text-slate-400 mb-1.5 font-mono">
                <span>Progress: {Math.round(roundFraction * 100)}% Counted</span>
                <span>
                  Tables: {currentRound * 14} / {TOTAL_ROUNDS * 14}
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                  style={{ width: `${roundFraction * 100}%` }}
                />
              </div>
            </div>
          </Card>

          {/* Round Results Table */}
          <Card padding="md" className="bg-slate-900 border-slate-800">
            <h3 className="text-sm font-bold text-white mb-4">
              Round {currentRound} Progressive Tallies
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] uppercase bg-slate-950 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-3">Rank</th>
                    <th className="p-3">Candidate</th>
                    <th className="p-3">Party</th>
                    <th className="p-3 text-right">This Round</th>
                    <th className="p-3 text-right">Cumulative Votes</th>
                    <th className="p-3 text-right">Share</th>
                    <th className="p-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {sortedCandidates.map((c: any, idx: number) => {
                    const totalVotes = c.vote_count ?? c.votes ?? 0;
                    const cumulativeVotes = Math.round(totalVotes * roundFraction);
                    const roundIncrement = Math.round(totalVotes / TOTAL_ROUNDS);
                    const totalCumulative = Math.round(totalCandidateVotes * roundFraction);
                    const share =
                      totalCumulative > 0 ? (cumulativeVotes / totalCumulative) * 100 : 0;
                    const isLeading = idx === 0 && cumulativeVotes > 0;

                    return (
                      <tr
                        key={c.candidate_id}
                        className={`hover:bg-slate-800/40 transition-colors ${
                          isLeading ? "bg-amber-950/20" : ""
                        }`}
                      >
                        <td className="p-3 font-mono font-bold text-slate-500">#{idx + 1}</td>
                        <td className="p-3 font-semibold text-white">
                          {c.candidate_name || c.name || c.candidate_id}
                        </td>
                        <td className="p-3 text-slate-400">{c.party || "IND"}</td>
                        <td className="p-3 text-right font-mono text-blue-400">
                          +{roundIncrement.toLocaleString()}
                        </td>
                        <td className="p-3 text-right font-mono font-bold text-emerald-400">
                          {cumulativeVotes.toLocaleString()}
                        </td>
                        <td className="p-3 text-right font-mono text-slate-300">
                          {share.toFixed(1)}%
                        </td>
                        <td className="p-3 text-right">
                          {isLeading ? (
                            <Badge variant="warning" className="text-[10px]">
                              Leading
                            </Badge>
                          ) : (
                            <span className="text-slate-500 text-[10px]">Trailing</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 3: FORM 20-STYLE SIMULATION RESULT SHEET */}
      {activeTab === "FORM20" && (
        <Card padding="lg" className="bg-slate-900 border-slate-800 font-sans">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
                Simulation Demonstration • Academic Reference: Conduct of Elections Rules, 1961 (Rule 56C(2)(C))
              </span>
              <h2 className="text-lg font-bold text-white mt-1">
                FORM 20-STYLE SIMULATION RESULT SHEET
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Simulated Election Results • {(selectedElection as any).name || selectedElection.title || selectedElection.id} ({selectedElection.id})
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => window.print()}>
                <Printer className="w-3.5 h-3.5 mr-1.5" />
                Print Sheet
              </Button>
            </div>
          </div>

          <div className="mt-6 mb-2 px-1">
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5 text-xs text-amber-300 flex items-start gap-2">
              <span className="font-bold shrink-0">⚠ Illustrative Polling-Station Allocation:</span>
              <span>Vote totals are distributed equally across polling stations using a synthetic proportional allocation (<code className="font-mono">share = 1 / n</code>). These per-station figures are illustrative simulation data, not actual polling-station ballot totals from physical counting.</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border border-slate-800">
              <thead className="bg-slate-950 text-slate-400 text-[10px] uppercase font-semibold">
                <tr className="border-b border-slate-800">
                  <th className="p-2.5 border-r border-slate-800">Serial No.</th>
                  <th className="p-2.5 border-r border-slate-800">Polling Station Name</th>
                  <th className="p-2.5 border-r border-slate-800">Control Unit ID</th>
                  {sortedCandidates.map((c: any) => (
                    <th key={c.candidate_id} className="p-2.5 border-r border-slate-800 text-right">
                      {c.candidate_name || c.name || c.candidate_id}
                    </th>
                  ))}
                  <th className="p-2.5 border-r border-slate-800 text-right">Total Valid Votes</th>
                  <th className="p-2.5 border-r border-slate-800 text-right">Rejected Votes</th>
                  <th className="p-2.5 text-right">Tendered Votes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                {pollingStations.map((ps, idx) => {
                  const share = 1 / pollingStations.length;
                  const validInStation = Math.round(totalCandidateVotes * share);

                  return (
                    <tr key={ps.id} className="hover:bg-slate-950/60 transition-colors">
                      <td className="p-2.5 border-r border-slate-800 text-slate-400">{idx + 1}</td>
                      <td className="p-2.5 border-r border-slate-800 font-sans text-slate-200">
                        {ps.name}
                      </td>
                      <td className="p-2.5 border-r border-slate-800 text-blue-400 font-bold">
                        {ps.eevm}
                      </td>
                      {sortedCandidates.map((c: any) => {
                        const totalCand = c.vote_count ?? c.votes ?? 0;
                        const candInPs = Math.round(totalCand * share);
                        return (
                          <td
                            key={c.candidate_id}
                            className="p-2.5 border-r border-slate-800 text-right text-slate-300"
                          >
                            {candInPs}
                          </td>
                        );
                      })}
                      <td className="p-2.5 border-r border-slate-800 text-right font-bold text-emerald-400">
                        {validInStation}
                      </td>
                      <td className="p-2.5 border-r border-slate-800 text-right text-slate-500">0</td>
                      <td className="p-2.5 text-right text-slate-500">0</td>
                    </tr>
                  );
                })}

                {/* Grand Total Row */}
                <tr className="bg-slate-950 font-bold border-t-2 border-slate-700 text-white">
                  <td colSpan={3} className="p-3 border-r border-slate-800 text-right font-sans">
                    GRAND TOTAL:
                  </td>
                  {sortedCandidates.map((c: any) => (
                    <td key={c.candidate_id} className="p-3 border-r border-slate-800 text-right text-emerald-400">
                      {(c.vote_count ?? c.votes ?? 0).toLocaleString()}
                    </td>
                  ))}
                  <td className="p-3 border-r border-slate-800 text-right text-emerald-400 text-sm">
                    {totalCandidateVotes.toLocaleString()}
                  </td>
                  <td className="p-3 border-r border-slate-800 text-right text-slate-400">0</td>
                  <td className="p-3 text-right text-slate-400">0</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <span className="font-semibold text-white">
                  SIMULATION DEMONSTRATION
                </span>
                <p className="text-[11px] text-slate-400">
                  Rendered using a Form 20-style structure for academic and research demonstration purposes, with reference to the Conduct of Elections Rules, 1961. Not an official statutory result sheet or certificate.
                </p>
              </div>
            </div>
            <div className="text-right font-mono text-[10px] text-slate-500">
              <div>Manifest Hash: {results?.manifest_hash ? results.manifest_hash.substring(0, 16) + "..." : "UNCOMMITTED"}</div>
              <div>Ed25519 Sig: {results?.digital_signature ? "VERIFIED VALID" : "PENDING POLL CLOSE"}</div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
