"use client";

import React from "react";
import { CandidateResponse } from "@/lib/types";

interface Props {
  candidate: CandidateResponse;
  isActive: boolean;
  isSelected: boolean;
  onClick: () => void;
}

export default function EvmCandidateButton({ candidate, isActive, isSelected, onClick }: Props) {
  // A crude way to get a color based on ID length or just use slate
  const symbolColor = candidate.party === "IND" ? "border-slate-500" : "border-indigo-500";

  return (
    <button
      onClick={onClick}
      disabled={!isActive}
      className={`
        flex items-center w-full bg-slate-800 border-2 rounded p-3 transition-all
        ${isActive ? "hover:bg-slate-700 cursor-pointer" : "opacity-60 cursor-not-allowed"}
        ${isSelected ? "border-amber-400 bg-slate-700 shadow-[0_0_15px_rgba(251,191,36,0.3)]" : "border-slate-600 shadow-sm"}
        border-l-8 ${symbolColor}
      `}
    >
      <div className="w-10 h-10 rounded-full bg-slate-900 flex items-center justify-center font-bold text-slate-300 font-mono text-lg shrink-0 border border-slate-700">
        {candidate.position}
      </div>

      <div className="ml-4 flex-1 text-left">
        <div className="font-bold text-lg text-slate-100">{candidate.name}</div>
        <div className="text-sm text-slate-400">{candidate.party || "Independent"} {candidate.symbol ? ` | ${candidate.symbol}` : ""}</div>
      </div>

      <div className="w-12 flex justify-center">
        <div className={`w-6 h-6 rounded-full border-2 ${isSelected ? 'bg-amber-500 border-amber-300 shadow-[0_0_10px_rgba(251,191,36,0.8)]' : 'bg-slate-900 border-slate-700'}`}></div>
      </div>
    </button>
  );
}
