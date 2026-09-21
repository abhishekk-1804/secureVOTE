"use client";
import React, { useState } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { Play, Lock, FileArchive, Flag, PowerOff, Loader2, Pause, Share2, CheckCircle2 } from "lucide-react";

export default function ElectionSetupPage() {
  const { selectedElection, refreshElections } = useElection();
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view setup.</div>;
  }

  const handleStateTransition = async (newState: string) => {
    if (loading) return;
    if (selectedElection.state === "PUBLISHED") {
      setError("Election is already in PUBLISHED terminal state. No further transitions permitted.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.updateElectionState(selectedElection.id, newState as any, token);
      await refreshElections();
    } catch (err: any) {
      // Re-fetch authoritative state on error/conflict
      await refreshElections();
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const steps = ["CREATED", "CONFIGURED", "LOCKED", "OPEN", "SUSPENDED", "CLOSED", "PUBLISHED"];
  const currentIndex = steps.indexOf(selectedElection.state);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Election Setup</h1>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">Lifecycle State</h2>
        <div className="flex items-center justify-between mb-8">
          {steps.map((step, i) => (
            <div key={step} className="flex flex-col items-center flex-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold mb-2
                ${i < currentIndex ? 'bg-emerald-500 text-slate-900' :
                  i === currentIndex ? 'bg-blue-500 text-white ring-4 ring-blue-500/30' :
                  'bg-slate-800 text-slate-500'}`}>
                {i + 1}
              </div>
              <span className={`text-[10px] uppercase font-bold tracking-wider ${i <= currentIndex ? 'text-slate-300' : 'text-slate-600'}`}>
                {step}
              </span>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-4 border-t border-slate-800 pt-6">
          {selectedElection.state === "PUBLISHED" ? (
            <div className="flex items-center justify-center gap-2 p-3 bg-purple-950/60 border border-purple-800/60 text-purple-300 rounded-lg text-sm font-semibold w-full">
              <CheckCircle2 className="w-5 h-5 text-purple-400" />
              <span>PUBLISHED — FINAL / TERMINAL STATE (Lifecycle Complete)</span>
            </div>
          ) : (
            <>
              {selectedElection.state === "CREATED" && (
                <button
                  onClick={() => handleStateTransition("CONFIGURED")}
                  disabled={loading}
                  className="flex-1 min-w-[140px] bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 py-2 px-4 rounded font-medium flex items-center justify-center gap-2"
                >
                  Configure
                </button>
              )}
              {selectedElection.state === "CONFIGURED" && (
                <button
                  onClick={() => handleStateTransition("LOCKED")}
                  disabled={loading}
                  className="flex-1 min-w-[140px] bg-amber-600/20 hover:bg-amber-600/30 text-amber-500 border border-amber-600/50 disabled:opacity-50 py-2 px-4 rounded font-medium flex items-center justify-center gap-2"
                >
                  <Lock className="w-4 h-4" /> Lock Configuration
                </button>
              )}
              {(selectedElection.state === "LOCKED" || selectedElection.state === "SUSPENDED") && (
                <button
                  onClick={() => handleStateTransition("OPEN")}
                  disabled={loading}
                  className="flex-1 min-w-[140px] bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-500 border border-emerald-600/50 disabled:opacity-50 py-2 px-4 rounded font-medium flex items-center justify-center gap-2"
                >
                  <Play className="w-4 h-4" /> {selectedElection.state === "SUSPENDED" ? "Resume Polls" : "Open Polls"}
                </button>
              )}
              {selectedElection.state === "OPEN" && (
                <button
                  onClick={() => handleStateTransition("SUSPENDED")}
                  disabled={loading}
                  className="flex-1 min-w-[140px] bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-600/50 disabled:opacity-50 py-2 px-4 rounded font-medium flex items-center justify-center gap-2"
                >
                  <Pause className="w-4 h-4" /> Suspend Polls
                </button>
              )}
              {(selectedElection.state === "OPEN" || selectedElection.state === "SUSPENDED") && (
                <button
                  onClick={() => handleStateTransition("CLOSED")}
                  disabled={loading}
                  className="flex-1 min-w-[140px] bg-rose-600/20 hover:bg-rose-600/30 text-rose-500 border border-rose-600/50 disabled:opacity-50 py-2 px-4 rounded font-medium flex items-center justify-center gap-2"
                >
                  <PowerOff className="w-4 h-4" /> Close Polls
                </button>
              )}
              {selectedElection.state === "CLOSED" && (
                <button
                  onClick={() => handleStateTransition("PUBLISHED")}
                  disabled={loading}
                  className="flex-1 min-w-[140px] bg-purple-600 hover:bg-purple-500 text-white disabled:opacity-50 py-2 px-4 rounded font-medium flex items-center justify-center gap-2"
                >
                  <Share2 className="w-4 h-4" /> Publish Results
                </button>
              )}
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4">Election Details</h2>
          <dl className="space-y-4 text-sm">
            <div>
              <dt className="text-slate-500">Title</dt>
              <dd className="font-medium text-slate-200">{selectedElection.title}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Description</dt>
              <dd className="text-slate-300">{selectedElection.description || "N/A"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Configuration Hash</dt>
              <dd className="font-mono text-xs text-blue-400 break-all">{selectedElection.configuration_hash || "Not generated yet"}</dd>
            </div>
          </dl>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4">Statistics</h2>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div className="bg-slate-800/50 p-4 rounded-lg">
              <dt className="text-slate-500 mb-1">Candidates</dt>
              <dd className="text-2xl font-bold text-slate-200">{selectedElection.candidates?.length ?? 0}</dd>
            </div>
            <div className="bg-slate-800/50 p-4 rounded-lg">
              <dt className="text-slate-500 mb-1">Devices</dt>
              <dd className="text-2xl font-bold text-slate-200">{selectedElection.device_count ?? 0}</dd>
            </div>
            <div className="bg-slate-800/50 p-4 rounded-lg col-span-2">
              <dt className="text-slate-500 mb-1">Ballots Cast</dt>
              <dd className="text-3xl font-bold text-emerald-400">{selectedElection.ballot_count ?? 0}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
