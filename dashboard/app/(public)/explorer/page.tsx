"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { StateFeature, ParliamentaryConstituency, PollingStationData, SyntheticCandidate } from "@/lib/types";
import {
  Search,
  Globe,
  MapPin,
  Building,
  Vote,
  ShieldCheck,
  Cpu,
  ChevronRight,
  ArrowRight,
  ExternalLink,
  Users,
} from "lucide-react";
import {
  StatCard,
  SecurityStatusBadge,
  ElectionBreadcrumb,
  ConstituencyCard,
} from "@/components/common";

export default function ExplorerPage() {
  const [states, setStates] = useState<any[]>([]);
  const [selectedStateCode, setSelectedStateCode] = useState<string>("KA");
  const [stateData, setStateData] = useState<any>(null);
  const [selectedPCId, setSelectedPCId] = useState<string>("KA-PC-24");
  const [pcData, setPCData] = useState<any>(null);
  const [pollingStations, setPollingStations] = useState<PollingStationData[]>([]);
  const [candidates, setCandidates] = useState<SyntheticCandidate[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStates = async () => {
      try {
        setLoading(true);
        const res = await api.getGeographyStates();
        setStates(res.states || []);
      } catch (err) {
        console.error("Failed to load states", err);
      } finally {
        setLoading(false);
      }
    };
    fetchStates();
  }, []);

  useEffect(() => {
    if (!selectedStateCode) return;
    const fetchStateDetails = async () => {
      try {
        const res = await api.getGeographyState(selectedStateCode);
        setStateData(res);
        const pcs = res.parliamentary_constituencies || res.constituencies || [];
        if (pcs.length > 0) {
          setSelectedPCId(pcs[0].pc_id || pcs[0].id);
        } else {
          setSelectedPCId("");
          setPCData(null);
          setPollingStations([]);
          setCandidates([]);
        }
      } catch (err) {
        console.error("Failed to load state details", err);
      }
    };
    fetchStateDetails();
  }, [selectedStateCode]);

  useEffect(() => {
    if (!selectedPCId) return;
    const fetchPC = async () => {
      try {
        const [pcRes, psRes, candRes] = await Promise.all([
          api.getGeographyPC(selectedPCId),
          api.getPCPollingStations(selectedPCId),
          api.getPCCandidates(selectedPCId),
        ]);
        setPCData(pcRes);
        setPollingStations(psRes.polling_stations || []);
        setCandidates(candRes.candidates || []);
      } catch (err) {
        console.error("Failed to load PC drilldown", err);
      }
    };
    fetchPC();
  }, [selectedPCId]);

  const filteredStates = states.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 md:p-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="inline-flex items-center gap-2 bg-emerald-500/10 text-emerald-400 text-xs font-semibold px-3 py-1 rounded-full border border-emerald-500/20 mb-2">
            <Globe className="w-3.5 h-3.5" /> PUBLIC ELECTORAL ROLL &amp; ARCHIVE EXPLORER
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            Constituency &amp; Polling Station Explorer
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Explore all 12 reference Indian States &amp; UTs, parliamentary constituencies, synthetic polling booths, assigned EVM triplets, and candidate rosters.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/map"
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-colors border border-slate-700 flex items-center gap-2"
          >
            <MapPin className="w-4 h-4 text-emerald-400" />
            Interactive SVG Map
          </Link>
          <Link
            href="/verify"
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-2"
          >
            <ShieldCheck className="w-4 h-4" />
            Verify Tally
          </Link>
        </div>
      </div>

      {/* Breadcrumb Bar */}
      <ElectionBreadcrumb
        stateCode={selectedStateCode}
        stateName={stateData?.name}
        pcId={selectedPCId}
        pcName={pcData?.name}
        onSelectState={setSelectedStateCode}
      />

      {/* Disclaimer Box */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 text-xs text-amber-300 flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
        <p>
          <span className="font-bold text-amber-400">RESEARCH PROTOTYPE DISCLAIMER:</span>{" "}
          State and Constituency names/counts represent real public Election Commission of India reference data. Registered voter numbers, turnouts, polling stations, candidates, and device serials are synthetic simulation datasets for academic cryptographic research.
        </p>
      </div>

      {/* State Quick Selector & Search */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Select State / Union Territory ({states.length} Active Jurisdictions)
          </h2>
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search state..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
          {filteredStates.map((s) => (
            <button
              key={s.code}
              onClick={() => setSelectedStateCode(s.code)}
              className={`p-3 rounded-lg border text-left transition-all text-xs flex flex-col justify-between ${
                s.code === selectedStateCode
                  ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300 font-semibold shadow-inner"
                  : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              <div className="font-bold text-white flex items-center justify-between">
                <span>{s.name}</span>
                <span className="font-mono text-[10px] text-slate-500">{s.code}</span>
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">
                {s.pc_count || s.total_pcs} PCs &bull; {s.ac_count || s.total_acs} ACs
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Content: Constituencies & Polling Station Drilldown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Parliamentary Constituencies in State */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Building className="w-4 h-4 text-purple-400" />
              Parliamentary Constituencies in {stateData?.name || selectedStateCode}
            </h2>
            <span className="text-xs font-mono text-slate-400">
              {(stateData?.parliamentary_constituencies || stateData?.constituencies || []).length} PCs
            </span>
          </div>

          <div className="space-y-3">
            {(stateData?.parliamentary_constituencies || stateData?.constituencies || []).map((pc: any) => (
              <ConstituencyCard
                key={pc.pc_id || pc.id}
                pc={pc}
                isSelected={(pc.pc_id || pc.id) === selectedPCId}
                onSelect={setSelectedPCId}
              />
            ))}
          </div>
        </div>

        {/* Right: Polling Stations & Candidates */}
        <div className="lg:col-span-7 space-y-6">
          {/* Candidates Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-400" />
                Ballot Candidates ({candidates.length}) &bull; {pcData?.name || selectedPCId}
              </h3>
              <span className="text-[10px] font-mono bg-blue-500/10 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded">
                Rule 49B NOTA Included
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {candidates.map((c) => (
                <div
                  key={c.id}
                  className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                    c.party === "NOTA"
                      ? "bg-amber-500/10 border-amber-500/30 text-amber-200"
                      : "bg-slate-950 border-slate-800 text-slate-200"
                  }`}
                >
                  <div>
                    <div className="font-bold flex items-center gap-2">
                      <span className="font-mono text-slate-500">#{c.position}</span>
                      <span>{c.name}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{c.party}</div>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
                      {c.symbol}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Polling Stations & Hardware Triplet */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Cpu className="w-4 h-4 text-emerald-400" />
                Simulated Polling Stations &amp; EVM Triplet Assignments
              </h3>
              <span className="text-xs font-mono text-slate-400">
                {pollingStations.length} Stations
              </span>
            </div>

            <div className="space-y-3">
              {pollingStations.map((station) => (
                <div
                  key={station.station_code}
                  className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-amber-300">
                          {station.station_code}
                        </span>
                        <SecurityStatusBadge status={station.status} size="sm" />
                      </div>
                      <h4 className="text-sm font-bold text-white mt-1">{station.station_name}</h4>
                      <p className="text-xs text-slate-400">{station.location}</p>
                    </div>

                    <div className="text-right sm:text-right font-mono text-xs">
                      <span className="text-slate-400 block text-[10px] uppercase">Ballots / Electors</span>
                      <span className="text-emerald-400 font-bold">
                        {station.ballots_cast} / {station.registered_voters} ({station.turnout_pct}%)
                      </span>
                    </div>
                  </div>

                  {/* Hardware Triplet: CU + BU + VVPAT */}
                  <div className="pt-2.5 border-t border-slate-800/80 grid grid-cols-3 gap-2 text-center text-xs font-mono">
                    <div className="bg-slate-900 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Control Unit</span>
                      <span className="text-blue-300 font-bold text-[11px]">{station.cu_serial}</span>
                    </div>
                    <div className="bg-slate-900 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Ballot Unit</span>
                      <span className="text-purple-300 font-bold text-[11px]">{station.bu_serial}</span>
                    </div>
                    <div className="bg-slate-900 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">VVPAT Unit (7s)</span>
                      <span className="text-emerald-300 font-bold text-[11px]">{station.vvpat_serial}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
