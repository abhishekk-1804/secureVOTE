"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import {
  MapPin,
  Layers,
  Globe,
  Building,
  Users,
  Activity,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";

export default function IndiaMapExplorerPage() {
  const [mapData, setMapData] = useState<{ viewbox: string; features: any[] } | null>(null);
  const [selectedStateCode, setSelectedStateCode] = useState<string>("KA");
  const [stateDetails, setStateDetails] = useState<any>(null);
  const [selectedPCId, setSelectedPCId] = useState<string>("KA-PC-24");
  const [pcDetails, setPCDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadingPC, setLoadingPC] = useState(false);

  useEffect(() => {
    const fetchMap = async () => {
      try {
        setLoading(true);
        const data = await api.getGeographyMapData();
        setMapData(data);
      } catch (err) {
        console.error("Failed to load map data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMap();
  }, []);

  useEffect(() => {
    if (!selectedStateCode) return;
    const fetchState = async () => {
      try {
        const data = await api.getGeographyState(selectedStateCode);
        setStateDetails(data);
        if (data.parliamentary_constituencies && data.parliamentary_constituencies.length > 0) {
          setSelectedPCId(data.parliamentary_constituencies[0].id);
        } else {
          setSelectedPCId("");
          setPCDetails(null);
        }
      } catch (err) {
        console.error("Failed to load state details", err);
      }
    };
    fetchState();
  }, [selectedStateCode]);

  useEffect(() => {
    if (!selectedPCId) return;
    const fetchPC = async () => {
      try {
        setLoadingPC(true);
        const data = await api.getGeographyPC(selectedPCId);
        setPCDetails(data);
      } catch (err) {
        console.error("Failed to load PC details", err);
      } finally {
        setLoadingPC(false);
      }
    };
    fetchPC();
  }, [selectedPCId]);

  const selectedFeature = mapData?.features.find((f) => f.code === selectedStateCode);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="inline-flex items-center gap-2 bg-emerald-500/10 text-emerald-400 text-xs font-semibold px-3 py-1 rounded-full border border-emerald-500/20 mb-2">
            <Globe className="w-3.5 h-3.5" /> INDIA ELECTORAL HIERARCHY EXPLORER
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            National, State & Constituency Map
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Simulated multi-tier hierarchy: National &rarr; State / UT &rarr; Parliamentary Constituency (PC) &rarr; Assembly Constituency (AC) &rarr; Polling Station.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/evm"
            className="px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm rounded-lg transition-colors flex items-center gap-2"
          >
            Launch EVM Terminal
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Geography Data Disclaimer */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-xs text-amber-300 flex items-start gap-2">
        <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
        <div>
          <span className="font-bold text-amber-400">REFERENCE / SIMULATION DATA:</span>
          {" "}All constituency counts, registered elector figures, and map geometry are approximate reference values compiled for academic and research demonstration only. Not an official ECI electoral roll/database.
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Interactive Map & State List */}
        <div className="lg:col-span-6 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <MapPin className="w-5 h-5 text-emerald-400" />
                Interactive Electoral Map
              </h2>
              <span className="text-xs text-slate-400 font-mono">Select a state</span>
            </div>

            {/* SVG India Map Schematic */}
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 flex items-center justify-center min-h-[380px]">
              {loading ? (
                <div className="flex items-center gap-2 text-slate-400 text-sm">
                  <Activity className="w-4 h-4 animate-spin text-emerald-400" />
                  Loading geography...
                </div>
              ) : (
                <svg
                  viewBox={mapData?.viewbox || "0 0 600 650"}
                  className="w-full max-h-[420px] drop-shadow-lg"
                >
                  {mapData?.features.map((feat) => {
                    const isSelected = feat.code === selectedStateCode;
                    return (
                      <g key={feat.code} className="cursor-pointer" onClick={() => setSelectedStateCode(feat.code)}>
                        <path
                          d={feat.svg_path}
                          className={`transition-all duration-300 stroke-2 ${
                            isSelected
                              ? "fill-emerald-500/40 stroke-emerald-400 filter drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                              : feat.has_active_simulation
                              ? "fill-amber-500/20 stroke-amber-400 hover:fill-amber-500/30"
                              : "fill-slate-800/80 stroke-slate-700 hover:fill-slate-700"
                          }`}
                        />
                        <text
                          x={feat.center ? feat.center[1] * 2.5 : 200}
                          y={feat.center ? 600 - feat.center[0] * 15 : 300}
                          textAnchor="middle"
                          className="fill-slate-300 text-[11px] font-bold pointer-events-none select-none"
                        >
                          {feat.code}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 mt-4 px-2">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-emerald-500/40 border border-emerald-400"></span>
                <span>Selected State</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-amber-500/20 border border-amber-400"></span>
                <span>Active Simulation (Karnataka)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-slate-800 border border-slate-700"></span>
                <span>Reference State</span>
              </div>
            </div>
          </div>

          {/* Quick Select State Chips */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              States & Union Territories
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {mapData?.features.map((s) => (
                <button
                  key={s.code}
                  onClick={() => setSelectedStateCode(s.code)}
                  className={`p-2.5 rounded-lg border text-left transition-all text-xs ${
                    s.code === selectedStateCode
                      ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300 font-semibold shadow-inner"
                      : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                  }`}
                >
                  <div className="font-bold">{s.name}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5 font-mono">{s.total_pcs} PCs | {s.total_acs} ACs</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: State Details & Constituency Drilldown */}
        <div className="lg:col-span-6 space-y-6">
          {/* State Card */}
          {stateDetails && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-mono text-emerald-400 uppercase tracking-wider">{stateDetails.region} Region</div>
                  <h2 className="text-2xl font-bold text-white">{stateDetails.name}</h2>
                </div>
                {stateDetails.active_simulation && (
                  <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs px-3 py-1 rounded-full font-bold">
                    LIVE SIMULATION ACTIVE
                  </span>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-xs text-slate-500">Parliamentary (PC)</span>
                  <p className="text-xl font-mono font-bold text-slate-100">{stateDetails.total_pcs}</p>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-xs text-slate-500">Assembly (AC)</span>
                  <p className="text-xl font-mono font-bold text-slate-100">{stateDetails.total_acs}</p>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-xs text-slate-500">Electors</span>
                  <p className="text-xl font-mono font-bold text-slate-100">{(stateDetails.registered_electors / 1000000).toFixed(1)}M</p>
                </div>
              </div>

              {/* Parliamentary Constituencies selection */}
              <div>
                <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                  Parliamentary Constituencies (PC)
                </label>
                <div className="flex flex-wrap gap-2">
                  {stateDetails.parliamentary_constituencies?.map((pc: any) => (
                    <button
                      key={pc.id}
                      onClick={() => setSelectedPCId(pc.id)}
                      className={`px-3 py-1.5 rounded-lg border text-xs transition-all font-mono ${
                        pc.id === selectedPCId
                          ? "bg-amber-500 text-slate-950 font-bold border-amber-400 shadow-md"
                          : "bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700"
                      }`}
                    >
                      PC-{pc.pc_number}: {pc.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* PC Details and ACs Drilldown */}
          {pcDetails && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
              <div className="border-b border-slate-800 pb-4">
                <div className="text-xs font-mono text-amber-400">PARLIAMENTARY CONSTITUENCY #{pcDetails.pc_number}</div>
                <h3 className="text-xl font-bold text-white flex items-center justify-between">
                  {pcDetails.name}
                  <span className="text-xs font-normal text-slate-400">Reservation: {pcDetails.reservation}</span>
                </h3>
              </div>

              {/* Assembly Constituencies List */}
              <div>
                <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                  <Building className="w-4 h-4 text-emerald-400" />
                  Assembly Constituencies (AC Segment)
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {pcDetails.assembly_constituencies?.map((ac: any) => (
                    <div key={ac.ac_number} className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex justify-between items-center text-xs">
                      <div>
                        <div className="font-medium text-slate-200">AC-{ac.ac_number}: {ac.name}</div>
                        <div className="text-[10px] text-slate-500 font-mono">{ac.reservation} Category</div>
                      </div>
                      <span className="text-slate-400 font-mono">{(ac.registered_voters / 1000).toFixed(0)}k</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Live Polling Stations in database */}
              <div>
                <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4 text-amber-400" />
                  Live Polling Stations in Simulation
                </h4>
                {pcDetails.live_polling_stations && pcDetails.live_polling_stations.length > 0 ? (
                  <div className="space-y-3">
                    {pcDetails.live_polling_stations.map((ps: any) => (
                      <div key={ps.id} className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                        <div>
                          <div className="font-bold text-sm text-slate-200 flex items-center gap-2">
                            <span className="text-amber-400 font-mono">{ps.station_code}</span>
                            {ps.name}
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5">{ps.location}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[10px] px-2.5 py-0.5 rounded font-mono font-bold">
                            {ps.status}
                          </span>
                          <Link
                            href="/evm"
                            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded transition-colors flex items-center gap-1 font-medium"
                          >
                            Launch Unit
                            <ExternalLink className="w-3 h-3" />
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-500 text-center">
                    No active polling stations provisioned in this constituency for the current simulation.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
