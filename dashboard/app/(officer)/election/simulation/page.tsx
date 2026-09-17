"use client";
import React, { useState } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { Play, Database, Server, Users, Activity } from "lucide-react";

export default function SimulationPage() {
  const { refreshElections } = useElection();
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preset, setPreset] = useState("DEMO_1000");
  const [result, setResult] = useState<any>(null);

  const handleRunSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.runSimulation({ preset, election_name: `Simulated Election (${preset})` }, token);
      setResult(data);
      await refreshElections();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Play className="w-6 h-6 text-blue-500" />
          System Simulation
        </h1>
      </div>

      <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-4 text-sm text-slate-300">
        Run load-testing simulations to generate synthetic election data (candidates, devices, voters, and ballots).
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">Configure Simulation</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Scale Preset</label>
              <select value={preset} onChange={e => setPreset(e.target.value)} disabled={loading} className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200">
                <option value="DEMO_1000">DEMO_1000 (Small Load Test)</option>
                <option value="DEMO_10000">DEMO_10000 (Medium Load Test)</option>
                <option value="DEMO_100000">DEMO_100000 (Large Load Test)</option>
              </select>
            </div>

            <button
              onClick={handleRunSimulation}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded-md font-medium flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? <Activity className="w-4 h-4 animate-pulse" /> : <Play className="w-4 h-4" />}
              {loading ? "Generating Data..." : "Run Simulation"}
            </button>
            {loading && <p className="text-xs text-center text-slate-500 mt-2">This may take several minutes for large presets.</p>}
          </div>
        </div>

        {result && (
          <div className="bg-slate-900 border border-emerald-800 rounded-lg p-6 border-t-4 border-t-emerald-500">
            <h2 className="text-lg font-medium mb-4 text-emerald-400 flex items-center gap-2"><CheckCircle2 className="w-5 h-5" /> Simulation Complete</h2>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-950 p-3 rounded border border-slate-800">
                <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Database className="w-3 h-3" /> Ballots Generated</div>
                <div className="text-xl font-bold font-mono text-slate-200">{result.ballots_generated || 0}</div>
              </div>
              <div className="bg-slate-950 p-3 rounded border border-slate-800">
                <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Server className="w-3 h-3" /> Devices Created</div>
                <div className="text-xl font-bold font-mono text-slate-200">{result.devices_created || 0}</div>
              </div>
              <div className="bg-slate-950 p-3 rounded border border-slate-800">
                <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Users className="w-3 h-3" /> Voters Registered</div>
                <div className="text-xl font-bold font-mono text-slate-200">{result.voters_registered || 0}</div>
              </div>
              <div className="bg-slate-950 p-3 rounded border border-slate-800">
                <div className="text-xs text-slate-500 mb-1">Duration</div>
                <div className="text-xl font-bold font-mono text-slate-200">{result.duration_ms ? `${(result.duration_ms/1000).toFixed(2)}s` : 'N/A'}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CheckCircle2(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}
