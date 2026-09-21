"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight, Globe, MapPin, Building, Cpu, Home } from "lucide-react";

export interface ElectionBreadcrumbProps {
  stateName?: string;
  stateCode?: string;
  pcName?: string;
  pcId?: string;
  pollingStationName?: string;
  stationCode?: string;
  deviceName?: string;
  onSelectState?: (code: string) => void;
  onSelectPC?: (id: string) => void;
}

export function ElectionBreadcrumb({
  stateName,
  stateCode,
  pcName,
  pcId,
  pollingStationName,
  stationCode,
  deviceName,
  onSelectState,
  onSelectPC,
}: ElectionBreadcrumbProps) {
  return (
    <nav
      aria-label="Electoral Hierarchy Breadcrumb"
      className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400 bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-2"
    >
      <Link
        href="/map"
        className="flex items-center gap-1 hover:text-white transition-colors text-slate-300 font-semibold"
      >
        <Globe className="w-3.5 h-3.5 text-emerald-400" />
        <span>India (National)</span>
      </Link>

      {stateCode && (
        <>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          {onSelectState ? (
            <button
              onClick={() => onSelectState(stateCode)}
              className="hover:text-white transition-colors text-slate-300 flex items-center gap-1"
            >
              <MapPin className="w-3 h-3 text-blue-400" />
              <span>{stateName || stateCode}</span>
            </button>
          ) : (
            <span className="text-slate-300 flex items-center gap-1">
              <MapPin className="w-3 h-3 text-blue-400" />
              <span>{stateName || stateCode}</span>
            </span>
          )}
        </>
      )}

      {pcId && (
        <>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          {onSelectPC ? (
            <button
              onClick={() => onSelectPC(pcId)}
              className="hover:text-white transition-colors text-slate-200 font-mono flex items-center gap-1"
            >
              <Building className="w-3 h-3 text-purple-400" />
              <span>{pcName || pcId}</span>
            </button>
          ) : (
            <span className="text-slate-200 font-mono flex items-center gap-1">
              <Building className="w-3 h-3 text-purple-400" />
              <span>{pcName || pcId}</span>
            </span>
          )}
        </>
      )}

      {stationCode && (
        <>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          <span className="text-amber-300 font-mono flex items-center gap-1 font-semibold">
            <span>{stationCode}</span>
            {pollingStationName && <span className="text-slate-400 font-normal">({pollingStationName})</span>}
          </span>
        </>
      )}

      {deviceName && (
        <>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          <span className="text-emerald-400 font-mono flex items-center gap-1 font-semibold">
            <Cpu className="w-3 h-3 text-emerald-400" />
            <span>{deviceName}</span>
          </span>
        </>
      )}
    </nav>
  );
}
