"use client";

import React from "react";
import EvmStatusLED from "./EvmStatusLED";

interface Props {
  state: string;
  sequenceNumber: number;
  isElectionOpen: boolean;
}

export default function EvmStatusPanel({ state, sequenceNumber, isElectionOpen }: Props) {
  const isSessionActive = ["CANDIDATE_SELECTION", "VOTE_CONFIRMED", "VOTE_SUBMITTED"].includes(state);

  return (
    <div className="bg-slate-900 border-2 border-slate-700 rounded-lg p-6 shadow-inner flex flex-col">
      <h3 className="text-slate-400 font-mono text-xs font-bold mb-4 border-b border-slate-800 pb-2">SYSTEM STATUS</h3>

      <div className="space-y-4 mb-8">
        <EvmStatusLED label="POWER" color="green" on={true} />
        <EvmStatusLED label="POLLING" color={isElectionOpen ? "green" : "red"} on={true} />
        <EvmStatusLED label="TAMPER" color="red" on={state === "ERROR"} />
        <EvmStatusLED label="SESSION" color="amber" on={isSessionActive} />
      </div>

      <div className="mt-auto">
        <div className="bg-slate-950 border-2 border-slate-800 rounded p-4 text-center">
          <div className="text-slate-500 text-xs font-mono mb-1">SEQUENCE NO.</div>
          <div className="text-amber-500 font-mono text-2xl font-bold tracking-widest">
            {sequenceNumber.toString().padStart(4, '0')}
          </div>
        </div>
      </div>
    </div>
  );
}
