"use client";

import React, { useState, useEffect } from "react";
import { CandidateResponse } from "@/lib/types";
import { Printer, Eye, CheckCircle2 } from "lucide-react";

export default function VVPATSlip({
  candidate,
  hash,
  isMockPoll,
  cryptoCommitment,
}: {
  candidate: CandidateResponse;
  hash: string;
  isMockPoll?: boolean;
  cryptoCommitment?: string | null;
}) {
  const [secondsRemaining, setSecondsRemaining] = useState(7);

  useEffect(() => {
    const interval = setInterval(() => {
      setSecondsRemaining((prev) => (prev > 1 ? prev - 1 : 1));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white text-slate-900 p-6 w-80 shadow-2xl border-4 border-slate-400 rounded-lg animate-in fade-in zoom-in duration-300 flex flex-col z-50">
      {/* VVPAT Inspection Window Frame */}
      <div className="flex items-center justify-between pb-3 border-b-2 border-slate-300 mb-3">
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-amber-600 animate-pulse" />
          <span className="text-xs font-bold font-mono tracking-wider text-slate-800">
            VVPAT VIEWING WINDOW
          </span>
        </div>
        <div className="text-[11px] font-mono font-bold bg-amber-100 text-amber-900 px-2 py-0.5 rounded border border-amber-300">
          {secondsRemaining}s REMAINING
        </div>
      </div>

      <div className="text-center font-bold text-[11px] text-slate-500 pb-2 border-b border-dashed border-slate-300 uppercase tracking-wide">
        Voter Verifiable Paper Audit Trail (VVPAT)
        <br />
        <span className="text-[10px] text-slate-400 font-normal">
          Slip visible for 7 seconds before dropping into sealed compartment
        </span>
      </div>

      {isMockPoll && (
        <div className="bg-rose-100 text-rose-900 font-bold text-center text-[10px] py-1 my-2 border border-rose-400 uppercase tracking-wider rounded">
          *** UI DIAGNOSTIC MODE — LOCAL PREVIEW ONLY ***
        </div>
      )}

      {/* Simulated Printed Paper Slip */}
      <div className="my-4 p-4 bg-slate-50 border-2 border-dashed border-slate-400 rounded font-mono text-center space-y-3">
        <div className="flex items-center justify-between text-xs border-b border-slate-300 pb-2">
          <span className="text-slate-500">SERIAL NO:</span>
          <span className="text-xl font-extrabold text-slate-900">
            {candidate.position}
          </span>
        </div>
        <div className="text-left">
          <span className="text-[10px] text-slate-400 block">CANDIDATE NAME</span>
          <span className="text-base font-bold text-slate-900 block leading-tight">
            {candidate.name}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-200">
          <div className="text-left">
            <span className="text-[10px] text-slate-400 block">PARTY</span>
            <span className="font-semibold text-slate-800">
              {candidate.party || "Independent"}
            </span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-slate-400 block">SYMBOL</span>
            <span className="font-bold text-slate-900 text-sm bg-white px-2 py-0.5 rounded border border-slate-300">
              {candidate.symbol || "★"}
            </span>
          </div>
        </div>
      </div>

      {/* 7-Second Countdown Bar */}
      <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden mb-3">
        <div
          className="bg-amber-500 h-full transition-all duration-1000 ease-linear"
          style={{ width: `${(secondsRemaining / 7) * 100}%` }}
        />
      </div>

      <div className="mt-auto pt-2 border-t border-dashed border-slate-300 text-[10px] text-center font-mono text-slate-500 flex flex-col gap-1">
        <div className="flex items-center justify-between w-full">
          <span>BALLOT HASH:</span>
          <span className="font-bold text-slate-700">
            {hash ? hash.substring(0, 16) : "PENDING"}...
          </span>
        </div>
        {cryptoCommitment && (
          <div className="flex items-center justify-between w-full text-[9px] text-indigo-700 bg-indigo-50 p-1 rounded border border-indigo-200">
            <span className="font-semibold">V3 COMMITMENT:</span>
            <span className="font-mono">{cryptoCommitment.substring(0, 14)}...</span>
          </div>
        )}
      </div>
    </div>
  );
}
