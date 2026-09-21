"use client";

import React from "react";
import { ParliamentaryConstituency } from "@/lib/types";
import { Building, Users, MapPin, CheckCircle, ChevronRight } from "lucide-react";
import Link from "next/link";
import clsx from "clsx";

export interface ConstituencyCardProps {
  pc: ParliamentaryConstituency | any;
  isSelected?: boolean;
  onSelect?: (pcId: string) => void;
  className?: string;
}

export function ConstituencyCard({
  pc,
  isSelected,
  onSelect,
  className,
}: ConstituencyCardProps) {
  const pcId = pc.pc_id || pc.id;
  const pcName = pc.pc_name || pc.name;
  const acList = pc.acs || pc.assembly_constituencies || [];
  const electors = pc.estimated_electors || pc.total_electors || 1800000;
  const turnout = pc.simulated_turnout_pct || pc.turnout_pct || 71.4;

  return (
    <div
      onClick={() => onSelect && onSelect(pcId)}
      className={clsx(
        "p-5 rounded-xl border transition-all text-left relative",
        isSelected
          ? "bg-slate-900 border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/40"
          : "bg-slate-900/90 border-slate-800 hover:border-slate-700 hover:bg-slate-900 shadow-md",
        onSelect && "cursor-pointer",
        className
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 uppercase tracking-wider font-semibold">
              {pc.state_code} &bull; PC-{pc.pc_no || pc.pc_number || pcId}
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              {pc.category || "GEN"}
            </span>
          </div>
          <h3 className="text-lg font-bold text-white mt-1">{pcName}</h3>
          <p className="text-xs text-slate-400">
            {pc.state_name || pc.state_code}
          </p>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-800/80 text-purple-400">
          <Building className="w-5 h-5" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 py-3 border-y border-slate-800/80 text-xs font-mono">
        <div>
          <span className="text-slate-500 block text-[10px] uppercase">Registered Electors</span>
          <span className="text-slate-200 font-bold">
            {(electors / 1000000).toFixed(2)}M
          </span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase">Simulated Turnout</span>
          <span className="text-emerald-400 font-bold">
            {turnout}%
          </span>
        </div>
      </div>

      {/* Assembly Segments preview */}
      <div className="mt-3">
        <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1 font-mono">
          Assembly Segments ({acList.length} ACs):
        </span>
        <div className="flex flex-wrap gap-1.5 max-h-16 overflow-y-auto pr-1">
          {acList.slice(0, 6).map((ac: any, idx: number) => (
            <span
              key={idx}
              className="text-[10px] bg-slate-950 border border-slate-800 text-slate-300 px-2 py-0.5 rounded"
            >
              {ac.ac_name || ac.name}
            </span>
          ))}
          {acList.length > 6 && (
            <span className="text-[10px] text-slate-500 self-center">
              +{acList.length - 6} more
            </span>
          )}
        </div>
      </div>

      {onSelect && (
        <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-emerald-400 font-semibold">
          <span>Explore Polling Stations & Candidates</span>
          <ChevronRight className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}
