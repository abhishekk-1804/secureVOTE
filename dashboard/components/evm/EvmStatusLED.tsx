"use client";

import React from "react";

export default function EvmStatusLED({ label, color, on }: { label: string, color: "green" | "red" | "amber", on: boolean }) {
  const colorMap = {
    green: "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.8)]",
    red: "bg-red-500 shadow-[0_0_12px_rgba(239,68,68,0.8)]",
    amber: "bg-amber-500 shadow-[0_0_12px_rgba(251,191,36,0.8)]"
  };

  return (
    <div className="flex items-center gap-3">
      <div className={`w-4 h-4 rounded-full border border-black ${on ? colorMap[color] : 'bg-slate-900'}`}></div>
      <span className="text-xs font-mono font-bold text-slate-300 tracking-wider">{label}</span>
    </div>
  );
}
