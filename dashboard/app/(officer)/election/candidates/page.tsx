"use client";
import React, { useState } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { Plus, Trash2, Lock } from "lucide-react";

export default function CandidatesPage() {
  const { selectedElection, refreshElections } = useElection();
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [party, setParty] = useState("");
  const [position, setPosition] = useState("1");

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view candidates.</div>;
  }

  const isLocked = selectedElection.state !== "CREATED" && selectedElection.state !== "CONFIGURED";

  const handleAddCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.addCandidate(selectedElection.id, { name, party, position: parseInt(position) || 1 }, token as string);
      await refreshElections();
      setName("");
      setParty("");
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (candidateId: string) => {
    setLoading(true);
    try {
      await api.deleteCandidate(selectedElection.id, candidateId, token as string);
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
        <h1 className="text-2xl font-bold tracking-tight">Candidate Management</h1>
        {isLocked && (
          <div className="flex items-center gap-2 bg-amber-500/10 text-amber-500 px-3 py-1.5 rounded-full text-xs font-medium border border-amber-500/20">
            <Lock className="w-3.5 h-3.5" />
            Configuration Locked
          </div>
        )}
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      {!isLocked && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4">Add Candidate</h2>
          <form onSubmit={handleAddCandidate} className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-400 mb-1">Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-400 mb-1">Party</label>
              <input
                type="text"
                required
                value={party}
                onChange={e => setParty(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-400 mb-1">Position</label>
              <input
                type="text"
                required
                value={position}
                onChange={e => setPosition(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded-md font-medium flex items-center gap-2 disabled:opacity-50"
            >
              <Plus className="w-4 h-4" /> Add
            </button>
          </form>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
            <tr>
              <th className="px-6 py-3 font-medium">Position</th>
              <th className="px-6 py-3 font-medium">ID</th>
              <th className="px-6 py-3 font-medium">Name</th>
              <th className="px-6 py-3 font-medium">Party</th>
              {!isLocked && <th className="px-6 py-3 font-medium text-right">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {selectedElection.candidates?.length ? (
              selectedElection.candidates.map(c => (
                <tr key={c.id} className="hover:bg-slate-800/20">
                  <td className="px-6 py-4">{c.position}</td>
                  <td className="px-6 py-4 font-mono text-xs text-slate-500">{c.id}</td>
                  <td className="px-6 py-4 font-medium">{c.name}</td>
                  <td className="px-6 py-4">{c.party}</td>
                  {!isLocked && (
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDelete(c.id)}
                        disabled={loading}
                        className="text-slate-400 hover:text-rose-400 p-1 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={isLocked ? 4 : 5} className="px-6 py-8 text-center text-slate-500">
                  No candidates registered yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
