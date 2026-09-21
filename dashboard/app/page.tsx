"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { StateFeature, NationalSummaryResponse } from "@/lib/types";
import {
  ShieldCheck,
  Globe,
  MapPin,
  Building,
  Vote,
  Users,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Cpu,
  Lock,
  ArrowRight,
  ExternalLink,
  Activity,
  ScrollText,
  KeyRound,
  Layers,
} from "lucide-react";
import {
  StatCard,
  SecurityStatusBadge,
  IndiaMap,
  TrusteeCard,
  CryptoPipeline,
} from "@/components/common";

const TRUSTEE_DATA = [
  {
    index: 1,
    name: "ECI Chief Election Commissioner",
    role: "Constitutional Election Authority",
    verificationKeyFingerprint: "04:b8:9f:32:81:c0:9a:71:3d:e8:f1:90:54:ab:cd:12",
    commitmentHash: "a8f9c0421e90d1952d7e5b128fae92bc44319082",
    isQual: true,
    hasSubmittedShare: true,
    status: "ONLINE" as const,
  },
  {
    index: 2,
    name: "IIT Madras Cryptography Lab",
    role: "Academic Cryptographic Auditor",
    verificationKeyFingerprint: "04:41:2d:7c:89:1e:bb:50:fa:93:c1:08:92:ef:33:aa",
    commitmentHash: "7b4c9102ef1920acbb83917409215ef82149b01c",
    isQual: true,
    hasSubmittedShare: true,
    status: "ONLINE" as const,
  },
  {
    index: 3,
    name: "Supreme Court Appointed Observer",
    role: "Independent Judicial Scrutiny",
    verificationKeyFingerprint: "04:90:c3:21:44:fa:71:0e:6b:19:82:dc:33:01:8b:f5",
    commitmentHash: "d193ef480291ba44c9215038fa9102c91839db04",
    isQual: true,
    hasSubmittedShare: true,
    status: "ONLINE" as const,
  },
];

const STATUTORY_LIFECYCLE_STAGES = [
  { step: "01", name: "Form 7A", desc: "List of Contesting Candidates Gazette Publication", status: "COMPLETED" },
  { step: "02", name: "First Randomization", desc: "Two-stage EVM allocation to ACs", status: "COMPLETED" },
  { step: "03", name: "Commissioning & Candidate Set", desc: "Setting ballot papers & seals on BU/CU", status: "COMPLETED" },
  { step: "04", name: "Second Randomization", desc: "Allocation to specific Polling Stations", status: "COMPLETED" },
  { step: "05", name: "Mock Poll (Rule 49E)", desc: "Mandatory 50-vote verification with polling agents", status: "COMPLETED" },
  { step: "06", name: "Poll Commencement", desc: "Clear CU memory, seal with green paper & special tag", status: "COMPLETED" },
  { step: "07", name: "Voting (Rule 49B NOTA)", desc: "Secrecy of voting, 7s VVPAT window, 1000Hz beep", status: "COMPLETED" },
  { step: "08", name: "Close of Poll (Rule 49M)", desc: "Press 'CLOSE' button on CU, record Form 17C", status: "COMPLETED" },
  { step: "09", name: "Strongroom Storage", desc: "Double lock, 24x7 CCTV, logbook maintenance", status: "COMPLETED" },
  { step: "10", name: "Counting (Rule 56D)", desc: "Table-wise round counting, Form 17C reconciliation", status: "COMPLETED" },
  { step: "11", name: "2-of-3 Threshold Decrypt", desc: "Verifiable partial decryptions with DLEQ proofs", status: "COMPLETED" },
  { step: "12", name: "Declaration of Result", desc: "Form 20 final result sheet & manifest signing", status: "COMPLETED" },
];

const RECENT_AUDIT_EVENTS = [
  {
    seq: 1042,
    time: "10:14:02 IST",
    type: "BALLOT_CAST_CRYPTOGRAPHIC",
    details: "ElGamal P-256 ciphertext + CDS94 proof recorded",
    jurisdiction: "KA-PC-24 / PS-042",
    hash: "3a8f...91c0",
  },
  {
    seq: 1041,
    time: "10:13:58 IST",
    type: "VVPAT_SLIP_VERIFIED",
    details: "7-second visual slip verification confirmed (Candidate #2)",
    jurisdiction: "KA-PC-24 / PS-042",
    hash: "e71b...04ab",
  },
  {
    seq: 1040,
    time: "10:13:50 IST",
    type: "RFID_VOTER_AUTHENTICATED",
    details: "Elector identity verified with hashed credential",
    jurisdiction: "KA-PC-24 / PS-042",
    hash: "902d...fa11",
  },
  {
    seq: 1039,
    time: "10:10:15 IST",
    type: "DKG_ROUND2_COMMITMENT_CHECK",
    details: "Feldman VSS polynomial commitments verified for all 3 trustees",
    jurisdiction: "NATIONAL / TRUSTEE-NET",
    hash: "55cc...8182",
  },
  {
    seq: 1038,
    time: "10:00:00 IST",
    type: "POLL_START_MOCK_POLL_CLEARED",
    details: "Mock poll 50 test votes cleared. Control Unit sealed.",
    jurisdiction: "KA-PC-24 / PS-001",
    hash: "110a...de44",
  },
];

export default function CommandCenterPage() {
  const [mapFeatures, setMapFeatures] = useState<StateFeature[]>([]);
  const [mapViewbox, setMapViewbox] = useState<string>("0 0 600 650");
  const [selectedStateCode, setSelectedStateCode] = useState<string>("KA");
  const [summary, setSummary] = useState<NationalSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [mapRes, summaryRes] = await Promise.all([
          api.getGeographyMapData(),
          api.getNationalSummary(),
        ]);
        setMapFeatures(mapRes.features || []);
        setMapViewbox(mapRes.viewbox || "0 0 600 650");
        setSummary(summaryRes);
      } catch (err) {
        console.error("Failed to load command center data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const selectedFeature = mapFeatures.find((f) => f.code === selectedStateCode) || mapFeatures[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-emerald-500 selection:text-white">
      {/* Top Research Disclaimer Banner */}
      <div className="bg-gradient-to-r from-amber-500/15 via-amber-500/10 to-amber-500/15 border-b border-amber-500/30 px-4 py-2.5 text-center text-xs text-amber-200">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-center gap-2">
          <span className="font-bold flex items-center gap-1.5 text-amber-300">
            <ShieldCheck className="w-4 h-4 text-amber-400" />
            RESEARCH PROTOTYPE &amp; INDIAN ELECTORAL SIMULATION:
          </span>
          <span>
            Independent research platform studying end-to-end verifiable voting and overseas consular voting proposals. Not an official Election Commission of India (ECI) system. Electoral geography names are compiled from public reference data; elector counts, turnouts, ballots, and devices are synthetic academic simulation models.
          </span>
        </div>
      </div>

      {/* Hero Section */}
      <section className="border-b border-slate-800 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-950 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 bg-emerald-500/10 text-emerald-400 text-xs font-semibold px-3 py-1 rounded-full border border-emerald-500/20">
                <Globe className="w-3.5 h-3.5" /> NATIONAL COMMAND &amp; VERIFICATION CENTER
              </div>
              <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white flex items-center gap-3">
                SECUREVOTE
                <span className="text-sm font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700 px-2.5 py-1 rounded-lg">
                  v3.3 Research
                </span>
              </h1>
              <p className="text-lg sm:text-xl text-slate-300 font-medium max-w-3xl">
                India Election Security &amp; Cryptographic Verification Research Platform
              </p>
              <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
                Combining authentic Indian voting ergonomics (CU, BU, 7-second VVPAT window, Rule 49B NOTA) with verifiable 2-of-3 threshold ElGamal decryption, CDS94 disjunctive zero-knowledge proofs, and offline deterministic replay verification.
              </p>
            </div>

            {/* Quick Action Buttons */}
            <div className="flex flex-wrap gap-2.5 shrink-0">
              <Link
                href="/evm"
                className="px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-amber-500/10"
              >
                <Vote className="w-4 h-4" />
                Launch EVM Terminal
              </Link>
              <Link
                href="/verify"
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-emerald-600/10"
              >
                <ShieldCheck className="w-4 h-4" />
                Run Independent Verifier
              </Link>
              <Link
                href="/explorer"
                className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs rounded-lg transition-colors border border-slate-700 flex items-center gap-2"
              >
                <Building className="w-4 h-4 text-purple-400" />
                Explore Constituencies
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Body */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
        {/* Section 1: 8 Main Stat Cards */}
        <section aria-label="Key National Metrics" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              National Overview &amp; Cryptographic State
            </h2>
            <SecurityStatusBadge status="VERIFIED" size="sm" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Active Pilot Election"
              value="KA-2026-001"
              subtitle="Karnataka Lok Sabha Simulation"
              icon={Vote}
              variant="info"
              badge="STATE: OPEN (RULE 49)"
            />
            <StatCard
              title="Reference States & UTs"
              value={summary?.total_states || 12}
              subtitle="All Indian geographical zones"
              icon={Globe}
              variant="default"
              badge="12 JURISDICTIONS"
            />
            <StatCard
              title="Constituencies"
              value={`${summary?.total_pcs || 64} PCs`}
              subtitle={`${summary?.total_acs || 512} Assembly Segments`}
              icon={Building}
              variant="purple"
              badge="LOK SABHA + AC HIERARCHY"
            />
            <StatCard
              title="Simulated Polling Stations"
              value="1,280"
              subtitle="Assigned CU + BU + VVPAT triplets"
              icon={Cpu}
              variant="default"
              badge="3,840 SIMULATED DEVICES"
            />
            <StatCard
              title="Simulated Research Ballots"
              value="142,850"
              subtitle="Additive ElGamal on secp256r1"
              icon={Lock}
              variant="success"
              badge="SIMULATED BENCHMARK"
            />
            <StatCard
              title="Verification Architecture"
              value="11-Point Check"
              subtitle="Mathematical recomputation pipeline"
              icon={CheckCircle2}
              variant="success"
              badge="INDEPENDENT REPLAY"
            />
            <StatCard
              title="Trustee Network Threshold"
              value="2-of-3 GJKR"
              subtitle="Distributed Key Generation (DKG)"
              icon={Users}
              variant="info"
              badge="ZERO TRUSTED DEALER"
            />
            <StatCard
              title="Detected Anomalies"
              value="0"
              subtitle="Advisory engine & drift check"
              icon={ShieldCheck}
              variant="default"
              badge="NO DISCREPANCIES"
            />
          </div>
        </section>

        {/* Section 2: Interactive India Map Centerpiece & State Profile */}
        <section aria-label="Interactive India Electoral Map" className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <MapPin className="w-5 h-5 text-emerald-400" />
                Interactive India Electoral Geography &amp; Turnout Map
              </h2>
              <p className="text-xs text-slate-400">
                Click any State / UT to inspect parliamentary constituencies, voter turnouts, and cryptographic verification status.
              </p>
            </div>
            <Link
              href="/explorer"
              className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1 self-start sm:self-auto"
            >
              View Full Roll Explorer <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            {/* Left: SVG India Map */}
            <div className="lg:col-span-7 flex flex-col justify-center items-center bg-slate-950 rounded-lg p-4 border border-slate-800/80">
              <IndiaMap
                features={mapFeatures}
                viewbox={mapViewbox}
                selectedStateCode={selectedStateCode}
                onSelectState={setSelectedStateCode}
              />
            </div>

            {/* Right: Selected State Detail Panel */}
            <div className="lg:col-span-5 flex flex-col justify-between space-y-6">
              {selectedFeature ? (
                <div className="space-y-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider font-semibold">
                        {selectedFeature.region} Region &bull; Code: {selectedFeature.code}
                      </span>
                      <h3 className="text-2xl font-bold text-white mt-0.5">
                        {selectedFeature.name}
                      </h3>
                      <p className="text-xs text-slate-400">
                        Capital: {selectedFeature.capital}
                      </p>
                    </div>

                    <SecurityStatusBadge
                      status={selectedFeature.code === "KA" ? "PILOT" : selectedFeature.verification_status}
                      size="md"
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-3 font-mono text-xs">
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Lok Sabha PCs</span>
                      <span className="text-lg font-bold text-white">{selectedFeature.pc_count || (selectedFeature as any).total_pcs}</span>
                    </div>
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Assembly ACs</span>
                      <span className="text-lg font-bold text-white">{selectedFeature.ac_count || (selectedFeature as any).total_acs}</span>
                    </div>
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Sim Turnout</span>
                      <span className="text-lg font-bold text-emerald-400">{selectedFeature.turnout_pct || (selectedFeature as any).turnout_percentage}%</span>
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between text-slate-400">
                      <span>Simulated Ballots Processed:</span>
                      <span className="font-mono text-slate-200 font-bold">
                        {selectedFeature.code === "KA" ? "142,850" : "Reference Baseline"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400">
                      <span>EVM Triplets Active:</span>
                      <span className="font-mono text-slate-200 font-bold">
                        {selectedFeature.code === "KA" ? "1,280 Units (CU/BU/VVPAT)" : "Standby Roll"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400">
                      <span>Cryptographic Audit Proof:</span>
                      <span className="font-mono text-emerald-400 font-semibold">
                        SHA-256 Intact (0 Discrepancies)
                      </span>
                    </div>
                  </div>

                  {selectedFeature.code === "KA" && (
                    <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-xs text-blue-200 space-y-1">
                      <div className="font-bold flex items-center gap-1.5 text-blue-300">
                        <Activity className="w-3.5 h-3.5" /> Active Pilot Jurisdiction
                      </div>
                      <p className="text-[11px] leading-relaxed text-blue-300/80">
                        Karnataka is configured with live voting simulations, candidate rosters (Rule 49B NOTA), and real-time append-only cryptographic logging.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-10 text-slate-500">
                  Select a state on the map to inspect details.
                </div>
              )}

              <div className="pt-4 border-t border-slate-800/80 flex gap-3">
                <Link
                  href="/explorer"
                  className="flex-1 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg transition-colors text-center"
                >
                  Explore Constituencies &amp; Boothers
                </Link>
                <Link
                  href="/evm"
                  className="py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-lg transition-colors text-center border border-slate-700"
                >
                  Launch Twin
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: Panel 1 & 2 - Election Integrity & Cryptographic Pipeline */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Panel 1: Statutory Indian Election Lifecycle */}
          <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <FileCheck className="w-5 h-5 text-amber-400" />
                  Indian Statutory Election Lifecycle
                </h3>
                <p className="text-xs text-slate-400">12-Stage ECI Operational &amp; Audit Architecture</p>
              </div>
              <span className="text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-semibold">
                ALL COMPLIANT
              </span>
            </div>

            <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-2">
              {STATUTORY_LIFECYCLE_STAGES.map((st) => (
                <div
                  key={st.step}
                  className="p-2.5 bg-slate-950 border border-slate-800/80 rounded-lg flex items-start gap-3 text-xs"
                >
                  <span className="font-mono font-bold text-emerald-400 text-[11px] pt-0.5">
                    {st.step}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-white truncate">{st.name}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5 leading-snug">{st.desc}</div>
                  </div>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                </div>
              ))}
            </div>
          </div>

          {/* Panel 2: Cryptographic Verification Pipeline */}
          <div className="lg:col-span-7">
            <CryptoPipeline />
          </div>
        </section>

        {/* Section 4: Panel 3 - 2-of-3 Trustee Network Panel */}
        <section aria-label="Trustee Network" className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-400" />
                Trustee Network: 2-of-3 Verifiable Threshold Decryption (GJKR DKG)
              </h2>
              <p className="text-xs text-slate-400">
                Joint public key derived without a trusted dealer. Any 2 trustees can tally; no single entity can decrypt ballots.
              </p>
            </div>
            <div className="text-xs font-mono bg-slate-900 border border-slate-800 px-3 py-1 rounded-lg text-slate-300 self-start sm:self-auto">
              Joint PK: <span className="text-emerald-400 font-bold">04:c9:81:...:7a</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TRUSTEE_DATA.map((trustee) => (
              <TrusteeCard key={trustee.index} {...trustee} />
            ))}
          </div>

          {/* Strict Security Isolation Notice */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 flex items-start gap-3">
            <Lock className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold text-white">CRYPTOGRAPHIC ZERO-SECRET ISOLATION GUARANTEE:</span>
              <p className="text-slate-400 leading-relaxed text-[11px]">
                Under the SecureVOTE 3.2 protocol specification, trustee secret shares (x1, x2, x3) and ephemeral random nonces (w) are never returned in responses, serialized into JSON packages, stored in the database, or transmitted over network interfaces. Only public verification keys (Yi), Feldman commitments (Ci,k), and Chaum-Pedersen proofs are exposed to the verifier.
              </p>
            </div>
          </div>
        </section>

        {/* Section 5: Panel 4 & 5 - Recent Audit Feed & System Health */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Panel 4: Append-Only Audit Chain Feed */}
          <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <ScrollText className="w-5 h-5 text-emerald-400" />
                  Append-Only Audit Log Feed
                </h3>
                <p className="text-xs text-slate-400">SHA-256 monotonic event hash chain</p>
              </div>
              <Link
                href="/election/audit"
                className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1"
              >
                Full Audit Explorer <ExternalLink className="w-3 h-3" />
              </Link>
            </div>

            <div className="space-y-2 font-mono text-xs">
              {RECENT_AUDIT_EVENTS.map((ev) => (
                <div
                  key={ev.seq}
                  className="bg-slate-950 border border-slate-800/80 rounded-lg p-3 space-y-1.5"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400 font-bold">#{ev.seq}</span>
                      <span className="text-slate-300 font-semibold">{ev.type}</span>
                    </div>
                    <span className="text-slate-500 text-[10px]">{ev.time}</span>
                  </div>
                  <div className="text-slate-400 text-[11px] font-sans">
                    {ev.details}
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-900">
                    <span>{ev.jurisdiction}</span>
                    <span className="text-slate-400">Hash: {ev.hash}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Panel 5: System & Device Health */}
          <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-blue-400" />
                  EVM Device &amp; System Health
                </h3>
                <p className="text-xs text-slate-400">Physical &amp; Digital Twin Telemetry</p>
              </div>
              <SecurityStatusBadge status="VERIFIED" size="sm" />
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                <div>
                  <div className="font-bold text-white">Control Unit (CU) Firmware</div>
                  <div className="text-[11px] text-slate-400">Monotonic Hardware Sequence Counter</div>
                </div>
                <span className="text-emerald-400 font-mono font-bold">ARMED</span>
              </div>

              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                <div>
                  <div className="font-bold text-white">Ballot Unit (BU) Integrity</div>
                  <div className="text-[11px] text-slate-400">Rule 49B NOTA Key Switch Active</div>
                </div>
                <span className="text-emerald-400 font-mono font-bold">ARMED</span>
              </div>

              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                <div>
                  <div className="font-bold text-white">VVPAT Slip Viewing Window</div>
                  <div className="text-[11px] text-slate-400">7.0-second visual audit timer &amp; drop chute</div>
                </div>
                <span className="text-emerald-400 font-mono font-bold">ARMED</span>
              </div>

              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                <div>
                  <div className="font-bold text-white">Hardware Tamper-Latch Flag</div>
                  <div className="text-[11px] text-slate-400">Accelerometer &amp; enclosure interlock</div>
                </div>
                <span className="text-emerald-400 font-mono font-bold">INTACT (0.0g)</span>
              </div>
            </div>

            <div className="pt-2">
              <Link
                href="/evm"
                className="w-full py-2.5 px-4 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <Vote className="w-4 h-4" />
                Launch Digital EVM Twin Simulator
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-8 px-4 text-center text-xs text-slate-500 space-y-2">
        <p className="font-mono text-slate-400">
          SECUREVOTE 3.3 &bull; India Election Security &amp; Cryptographic Verification Research Platform
        </p>
        <p className="text-[11px] text-slate-600 max-w-2xl mx-auto">
          Built on SECP256R1 Additive ElGamal &bull; CDS94 Disjunctive ZKP &bull; GJKR 2-of-3 Threshold Decryption &bull; Ed25519 Manifests &bull; Deterministic Replay Verification.
        </p>
      </footer>
    </div>
  );
}
