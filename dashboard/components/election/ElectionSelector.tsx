"use client";
import React from "react";
import { useElection } from "@/context/ElectionContext";

export function ElectionSelector() {
  const { elections, selectedElection, selectElection, loading } = useElection();

  if (loading) {
    return <div className="animate-pulse bg-slate-800 h-8 w-48 rounded-md"></div>;
  }

  if (elections.length === 0) {
    return <span className="text-xs text-slate-500">No elections found</span>;
  }

  return (
    <select
      className="bg-slate-800 border border-slate-700 text-sm text-slate-200 rounded-md py-1 px-2 focus:outline-none focus:border-blue-500"
      value={selectedElection?.id || ""}
      onChange={(e) => selectElection(e.target.value)}
      aria-label="Select Election"
    >
      {elections.map((election) => (
        <option key={election.id} value={election.id}>
          {election.name || (election as any).title || election.id} ({election.state})
        </option>
      ))}
    </select>
  );
}
