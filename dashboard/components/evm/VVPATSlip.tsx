"use client";

import React from "react";
import { CandidateResponse } from "@/lib/types";
import { Printer } from "lucide-react";

export default function VVPATSlip({ candidate, hash, isMockPoll }: { candidate: CandidateResponse, hash: string, isMockPoll?: boolean }) {
  return (
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white text-black p-6 w-72 shadow-2xl border-4 border-slate-300 animate-in fade-in zoom-in duration-300 flex flex-col z-50">
      <div className="flex justify-center mb-4 text-slate-400">
        <Printer className="w-8 h-8" />
      </div>
      <div className="text-center font-bold text-xs mb-2 pb-2 border-b-2 border-dashed border-slate-300">
        VVPAT-INSPIRED PROTOTYPE<br/>
        NOT OFFICIAL
      </div>

      {isMockPoll && (
        <div className="bg-rose-100 text-rose-900 font-bold text-center text-[10px] py-1 mb-2 border border-rose-400 uppercase tracking-wider">
          *** UI DIAGNOSTIC MODE — TEST ONLY — NO BACKEND BALLOT ***
        </div>
      )}

      <div className="text-center space-y-4 mb-6">
        <div className="text-4xl font-bold">{candidate.position}</div>
        <div className="text-xl font-bold">{candidate.name}</div>
        <div className="text-lg">{candidate.party || "Independent"}</div>
        <div className="text-lg">{candidate.symbol}</div>
      </div>

      <div className="mt-auto pt-4 border-t-2 border-dashed border-slate-300 text-xs text-center font-mono break-all text-slate-500">
        HASH: {hash.substring(0, 16)}...
      </div>
    </div>
  );
}
