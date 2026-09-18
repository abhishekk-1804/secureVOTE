"use client";

import React, { useState } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import {
  Play,
  Database,
  Server,
  Users,
  Activity,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function SimulationPage() {
  const { refreshElections } = useElection();
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [seedLoading, setSeedLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [preset, setPreset] = useState("DEMO_1000");
  const [result, setResult] = useState<any>(null);

  const handleRunSimulation = async () => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const data = await api.runSimulation(
        { preset, election_name: `Simulated Election (${preset})` },
        token
      );
      setResult(data);
      setSuccessMsg(`Successfully generated simulated election: ${data.election_id || "EV-2026-SIM"}`);
      await refreshElections();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSeedGoldenDemo = async () => {
    setSeedLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const data = await api.seedDemoElection(token);
      setSuccessMsg(`Golden Demo Election (EV-2026-001) seeded successfully with 4 candidates and 20 eligible voters!`);
      await refreshElections();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setSeedLoading(false);
    }
  };

  const presets = [
    {
      id: "DEMO_1000",
      name: "Small Scale (DEMO_1000)",
      voters: "1,000 Voters",
      stations: "2 Stations",
      devices: "4 EVM Units",
      candidates: "4 Candidates",
      turnout: "~700 Ballots",
      desc: "Fast in-memory load test ideal for UI smoke testing and verifier benchmarks.",
    },
    {
      id: "DEMO_10000",
      name: "Constituency Segment (DEMO_10000)",
      voters: "10,000 Voters",
      stations: "10 Stations",
      devices: "20 EVM Units",
      candidates: "6 Candidates",
      turnout: "~7,000 Ballots",
      desc: "Comprehensive multi-polling-station dataset for round-by-round counting verification.",
    },
    {
      id: "DEMO_100000",
      name: "India Assembly Scale (DEMO_100000)",
      voters: "100,000 Voters",
      stations: "50 Stations",
      devices: "100 EVM Units",
      candidates: "8 Candidates",
      turnout: "~70,000 Ballots",
      desc: "High-density stress test verifying cryptographic hash chain scalability.",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2 text-white">
            <Play className="w-5 h-5 text-blue-500" />
            Ecosystem Simulation & Load Engine
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic synthetic generation of complete Indian electoral hierarchies, EVM units, and audit chains
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSeedGoldenDemo}
            loading={seedLoading}
          >
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
            Seed Golden Demo (EV-2026-001)
          </Button>
        </div>
      </div>

      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 px-4 py-3 rounded-xl flex items-center gap-2 text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          {successMsg}
        </div>
      )}

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 text-rose-400 px-4 py-3 rounded-xl flex items-center gap-2 text-xs">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Scale Presets */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-400" />
            Select Synthetic Scale Preset
          </h2>

          <div className="grid grid-cols-1 gap-3">
            {presets.map((p) => {
              const isSelected = preset === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => setPreset(p.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? "bg-slate-900 border-blue-500 ring-1 ring-blue-500/40"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-sm font-bold text-white flex items-center gap-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          isSelected ? "bg-blue-400" : "bg-slate-700"
                        }`}
                      />
                      {p.name}
                    </span>
                    <Badge variant={isSelected ? "info" : "neutral"} className="text-[10px]">
                      {p.turnout}
                    </Badge>
                  </div>

                  <p className="text-xs text-slate-400 mb-3">{p.desc}</p>

                  <div className="flex flex-wrap gap-2 text-[11px] font-mono text-slate-300">
                    <span className="bg-slate-950 px-2 py-1 rounded border border-slate-800">
                      {p.voters}
                    </span>
                    <span className="bg-slate-950 px-2 py-1 rounded border border-slate-800">
                      {p.stations}
                    </span>
                    <span className="bg-slate-950 px-2 py-1 rounded border border-slate-800">
                      {p.devices}
                    </span>
                    <span className="bg-slate-950 px-2 py-1 rounded border border-slate-800">
                      {p.candidates}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-2">
            <Button
              variant="primary"
              size="lg"
              className="w-full"
              onClick={handleRunSimulation}
              loading={loading}
            >
              <Play className="w-4 h-4 mr-2" />
              {loading ? "Generating Full Cryptographic State..." : `Run ${preset} Simulation`}
            </Button>
            {loading && (
              <p className="text-[11px] text-center text-slate-400 mt-2 font-mono">
                Calculating canonical SHA-256 hash chains and deterministic digital Twin registers...
              </p>
            )}
          </div>
        </div>

        {/* Right Col: Output Metrics */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-white">Simulation Output</h2>

          {result ? (
            <Card padding="md" className="bg-slate-900 border-emerald-800/60 border-t-4 border-t-emerald-500">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs mb-3">
                <CheckCircle2 className="w-4 h-4" />
                Simulation Run Complete
              </div>

              <div className="space-y-2.5 text-xs font-mono">
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 flex justify-between items-center">
                  <span className="text-slate-400 flex items-center gap-1.5 font-sans">
                    <Database className="w-3.5 h-3.5 text-blue-400" /> Ballots Cast
                  </span>
                  <span className="font-bold text-white">
                    {(result.ballots_generated || 0).toLocaleString()}
                  </span>
                </div>

                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 flex justify-between items-center">
                  <span className="text-slate-400 flex items-center gap-1.5 font-sans">
                    <Users className="w-3.5 h-3.5 text-indigo-400" /> Voters Enrolled
                  </span>
                  <span className="font-bold text-white">
                    {(result.voters_registered || 0).toLocaleString()}
                  </span>
                </div>

                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 flex justify-between items-center">
                  <span className="text-slate-400 flex items-center gap-1.5 font-sans">
                    <Server className="w-3.5 h-3.5 text-purple-400" /> Active EVMs
                  </span>
                  <span className="font-bold text-white">
                    {result.devices_created || 0}
                  </span>
                </div>

                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 flex justify-between items-center">
                  <span className="text-slate-400 flex items-center gap-1.5 font-sans">
                    <Activity className="w-3.5 h-3.5 text-emerald-400" /> Execution Time
                  </span>
                  <span className="font-bold text-emerald-400">
                    {result.duration_ms ? `${(result.duration_ms / 1000).toFixed(2)}s` : "N/A"}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800 flex flex-col gap-2">
                <Link
                  href="/election/counting"
                  className="w-full bg-slate-800 hover:bg-slate-700 text-white text-xs py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 font-medium transition-colors"
                >
                  Inspect Counting Center
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href="/evm"
                  className="w-full bg-slate-800/60 hover:bg-slate-800 text-slate-300 text-xs py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 font-medium transition-colors border border-slate-700/60"
                >
                  Launch Digital EVM Terminal
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </Card>
          ) : (
            <Card padding="md" className="bg-slate-900/60 border-slate-800 text-center py-8">
              <Database className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">
                Run a simulation or seed the golden demo election to inspect synthetic ballots and cryptographic audit trails.
              </p>
            </Card>
          )}

          <div className="bg-blue-950/20 border border-blue-800/40 rounded-xl p-3.5 text-[11px] text-blue-300">
            <span className="font-bold text-white">Reproducibility Notice:</span> All simulated electoral runs generate deterministic pseudorandom datasets using seed keys derived from the election ID.
          </div>
        </div>
      </div>
    </div>
  );
}
