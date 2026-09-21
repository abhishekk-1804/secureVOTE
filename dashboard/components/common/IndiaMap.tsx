"use client";

import React, { useState } from "react";
import { StateFeature } from "@/lib/types";
import { Info, MapPin } from "lucide-react";
import clsx from "clsx";

export interface IndiaMapProps {
  features: StateFeature[];
  selectedStateCode?: string;
  onSelectState?: (code: string) => void;
  viewbox?: string;
  className?: string;
  showTooltip?: boolean;
}

export function IndiaMap({
  features,
  selectedStateCode,
  onSelectState,
  viewbox = "0 0 600 650",
  className,
  showTooltip = true,
}: IndiaMapProps) {
  const [hoveredState, setHoveredState] = useState<StateFeature | null>(null);

  const getStateFill = (feat: StateFeature) => {
    const isSelected = feat.code === selectedStateCode;
    if (isSelected) {
      return "fill-emerald-500/40 stroke-emerald-400 filter drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]";
    }
    if (feat.code === "KA") {
      return "fill-blue-500/30 stroke-blue-400 hover:fill-blue-500/50";
    }
    if (feat.verification_status === "WARNING") {
      return "fill-amber-500/30 stroke-amber-400 hover:fill-amber-500/50";
    }
    if (feat.verification_status === "VERIFIED") {
      return "fill-emerald-600/20 stroke-emerald-500/60 hover:fill-emerald-600/35";
    }
    return "fill-slate-800/90 stroke-slate-700 hover:fill-slate-700/90";
  };

  return (
    <div className={clsx("relative w-full flex flex-col items-center", className)}>
      {/* SVG Container */}
      <div className="relative w-full max-w-lg aspect-[600/650] flex items-center justify-center">
        <svg
          viewBox={viewbox}
          className="w-full h-full drop-shadow-2xl select-none"
          role="region"
          aria-label="Interactive India Electoral Simulation Map"
        >
          {features.map((feat) => {
            const isSelected = feat.code === selectedStateCode;
            const pathD = feat.d || (feat as any).svg_path;
            if (!pathD) return null;

            return (
              <g
                key={feat.code}
                className="cursor-pointer group focus:outline-none"
                onClick={() => onSelectState && onSelectState(feat.code)}
                onMouseEnter={() => setHoveredState(feat)}
                onMouseLeave={() => setHoveredState(null)}
                tabIndex={0}
                role="button"
                aria-label={`${feat.name} (${feat.code}): ${feat.pc_count || (feat as any).total_pcs} Lok Sabha Constituencies, Turnout ${feat.turnout_pct || (feat as any).turnout_percentage}%`}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectState && onSelectState(feat.code);
                  }
                }}
              >
                <path
                  d={pathD}
                  className={clsx(
                    "transition-all duration-200 stroke-[2px]",
                    getStateFill(feat)
                  )}
                />
                {feat.center && (
                  <text
                    x={feat.center[1] * 2.5}
                    y={600 - feat.center[0] * 15}
                    textAnchor="middle"
                    className={clsx(
                      "text-[10px] font-bold pointer-events-none select-none font-mono transition-colors",
                      isSelected ? "fill-emerald-200 font-extrabold text-[12px]" : "fill-slate-300"
                    )}
                  >
                    {feat.code}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Floating Tooltip */}
        {showTooltip && hoveredState && (
          <div
            className="absolute bottom-4 left-4 right-4 sm:right-auto sm:w-64 bg-slate-900/95 border border-slate-700 text-slate-100 p-3 rounded-lg shadow-2xl backdrop-blur-md pointer-events-none z-20 animate-in fade-in zoom-in-95 duration-150"
            role="status"
            aria-live="polite"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 mb-1.5">
              <span className="font-bold text-sm text-white flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                {hoveredState.name}
              </span>
              <span className="font-mono text-xs text-slate-400 font-semibold bg-slate-800 px-1.5 py-0.5 rounded">
                {hoveredState.code}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
              <div>
                <span className="text-slate-400 block">Constituencies:</span>
                <span className="text-slate-200 font-semibold">
                  {hoveredState.pc_count || (hoveredState as any).total_pcs} PCs / {hoveredState.ac_count || (hoveredState as any).total_acs} ACs
                </span>
              </div>
              <div>
                <span className="text-slate-400 block">Turnout (Sim):</span>
                <span className="text-emerald-400 font-semibold">
                  {hoveredState.turnout_pct || (hoveredState as any).turnout_percentage}%
                </span>
              </div>
            </div>
            <div className="mt-1.5 pt-1.5 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
              <span className="text-slate-400">Capital: {hoveredState.capital}</span>
              <span
                className={clsx(
                  "px-1.5 py-0.2 rounded font-semibold",
                  hoveredState.code === "KA"
                    ? "bg-blue-500/20 text-blue-300"
                    : hoveredState.verification_status === "VERIFIED"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-slate-800 text-slate-300"
                )}
              >
                {hoveredState.code === "KA" ? "PILOT STATE" : hoveredState.verification_status}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Map Legend */}
      <div className="w-full mt-4 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-400 border-t border-slate-800/80 pt-3">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-emerald-500/40 border border-emerald-400"></span>
          <span>Selected</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-blue-500/30 border border-blue-400"></span>
          <span>Karnataka (Pilot)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-emerald-600/20 border border-emerald-500/60"></span>
          <span>Verified State</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-slate-800 border border-slate-700"></span>
          <span>Reference Roll</span>
        </div>
      </div>

      {/* Accessible Select Dropdown for Screen Readers / Quick Navigation */}
      <div className="w-full mt-3 flex items-center justify-between bg-slate-900/60 border border-slate-800 rounded-lg p-2 text-xs">
        <label htmlFor="state-map-selector" className="text-slate-400 flex items-center gap-1 font-medium">
          <Info className="w-3.5 h-3.5 text-slate-400" />
          <span>Quick Select:</span>
        </label>
        <select
          id="state-map-selector"
          value={selectedStateCode || ""}
          onChange={(e) => onSelectState && onSelectState(e.target.value)}
          className="bg-slate-950 border border-slate-700 text-slate-200 rounded px-2.5 py-1 text-xs focus:ring-1 focus:ring-emerald-500 focus:outline-none"
        >
          <option value="">-- Choose State / UT --</option>
          {features.map((f) => (
            <option key={f.code} value={f.code}>
              {f.name} ({f.code}) — {f.pc_count || (f as any).total_pcs} PCs
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
