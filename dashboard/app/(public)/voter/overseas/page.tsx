"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import {
  Globe2,
  FileCheck2,
  Building2,
  Shield,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Plane,
  KeyRound,
  FileText,
  Lock,
} from "lucide-react";

export default function OverseasVotingPage() {
  const [activeTab, setActiveTab] = useState<"mode_a" | "mode_b">("mode_a");
  const [framework, setFramework] = useState<any>(null);

  // Form 6A State (Mode A)
  const [fullName, setFullName] = useState("Rohit Verma");
  const [passportNumber, setPassportNumber] = useState("Z8941275");
  const [country, setCountry] = useState("United States");
  const [visaType, setVisaType] = useState("H-1B Specialty Occupation");
  const [constituency, setConstituency] = useState("Bengaluru Central");
  const [dob, setDob] = useState("1989-08-14");
  const [form6aResult, setForm6aResult] = useState<any>(null);
  const [submitting6A, setSubmitting6A] = useState(false);

  // Mode B Consular Simulation State
  const [consulateCity, setConsulateCity] = useState("San Francisco");
  const [consularResult, setConsularResult] = useState<any>(null);
  const [simulatingConsular, setSimulatingConsular] = useState(false);

  useEffect(() => {
    const loadFramework = async () => {
      try {
        const data = await api.getOverseasFramework();
        setFramework(data);
      } catch (err) {
        console.error("Failed to load overseas framework", err);
      }
    };
    loadFramework();
  }, []);

  const handleForm6ASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting6A(true);
      const res = await api.submitForm6A({
        full_name: fullName,
        passport_number: passportNumber,
        country_of_residence: country,
        visa_type: visaType,
        home_constituency: constituency,
        date_of_birth: dob,
      });
      setForm6aResult(res);
    } catch (err: any) {
      alert(`Submission failed: ${err.message}`);
    } finally {
      setSubmitting6A(false);
    }
  };

  const handleConsularSimulate = async () => {
    try {
      setSimulatingConsular(true);
      const res = await api.simulateConsularSession({
        passport_number: passportNumber,
        country: country,
        consulate_city: consulateCity,
        election_id: "EV-2026-001",
      });
      setConsularResult(res);
    } catch (err: any) {
      alert(`Simulation failed: ${err.message}`);
    } finally {
      setSimulatingConsular(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 text-indigo-400 text-xs font-semibold px-3 py-1 rounded-full border border-indigo-500/20 mb-2">
            <Globe2 className="w-3.5 h-3.5" /> DUAL-MODE OVERSEAS (NRI) CITIZEN ELECTOR SIMULATION
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            Overseas / NRI Elector Portal
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            Simulating both the current statutory in-person voting framework (Form 6A under RPA 1950 &sect;20A) and the SecureVOTE dual-control consular research protocol.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab("mode_a")}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
              activeTab === "mode_a"
                ? "bg-amber-500 text-slate-950 shadow-md"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Mode A: Current Statutory Rule
          </button>
          <button
            onClick={() => setActiveTab("mode_b")}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
              activeTab === "mode_b"
                ? "bg-indigo-600 text-white shadow-md"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Mode B: Consular Research Lab
          </button>
        </div>
      </div>

      {/* Mode A: Statutory In-Person Rule */}
      {activeTab === "mode_a" && (
        <div className="space-y-6">
          <div className="bg-amber-500/10 border border-amber-500/30 p-4 rounded-xl flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-300 space-y-1">
              <span className="font-bold text-amber-400">Current Law Under Representation of the People Act, 1950 (&sect;20A):</span>
              <p>
                An overseas elector (NRI) who has not acquired citizenship of any other country is eligible to be registered in the electoral roll of their constituency in India using Form 6A.
                However, under current law, <span className="underline font-semibold text-white">no remote or postal voting is permitted for overseas electors</span> &mdash; the elector must physically travel to India and cast their vote in person at their registered polling booth with their original passport.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Form 6A Application */}
            <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <FileText className="w-5 h-5 text-amber-400" />
                  Simulate Form 6A Overseas Enrollment
                </h2>
                <span className="text-xs text-slate-400 font-mono">Form 6A (Sec 20A)</span>
              </div>

              <div className="bg-rose-950/40 border border-rose-500/40 rounded-lg p-2.5 text-[11px] text-rose-300 flex items-start gap-2">
                <span className="font-bold shrink-0 text-rose-400">⚠ SYNTHETIC DATA ONLY:</span>
                <span>USE SYNTHETIC TEST DATA ONLY. DO NOT ENTER REAL PASSPORT INFORMATION. This is an educational simulation — no real voter registration is performed.</span>
              </div>

              <form onSubmit={handleForm6ASubmit} className="space-y-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-400 mb-1">Full Legal Name (as in Passport)</label>
                    <input
                      type="text"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-amber-500"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">Passport Number (Indian Passport)</label>
                    <input
                      type="text"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono outline-none focus:border-amber-500"
                      value={passportNumber}
                      onChange={(e) => setPassportNumber(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-400 mb-1">Current Country of Residence</label>
                    <input
                      type="text"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-amber-500"
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">Overseas Visa / Residence Category</label>
                    <input
                      type="text"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-amber-500"
                      value={visaType}
                      onChange={(e) => setVisaType(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-400 mb-1">Home Constituency in India</label>
                    <input
                      type="text"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-amber-500"
                      value={constituency}
                      onChange={(e) => setConstituency(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">Date of Birth</label>
                    <input
                      type="date"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-amber-500"
                      value={dob}
                      onChange={(e) => setDob(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submitting6A}
                  className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg transition-colors flex items-center justify-center gap-2 text-sm disabled:opacity-50"
                >
                  {submitting6A ? "Processing Application..." : "Submit Simulated Form 6A Application"}
                </button>
              </form>
            </div>

            {/* Application Receipt & Statutory Verification */}
            <div className="lg:col-span-5 space-y-6">
              {form6aResult ? (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                    <CheckCircle2 className="w-5 h-5" />
                    Form 6A Enrollment Simulated
                  </div>

                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-xs space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Ref Number:</span>
                      <span className="font-mono text-amber-400 font-bold">{form6aResult.reference_number}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Applicant:</span>
                      <span className="text-slate-200">{form6aResult.applicant_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Passport Pseudonym:</span>
                      <span className="font-mono text-slate-300">{form6aResult.passport_pseudonym}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Allocated Station:</span>
                      <span className="text-emerald-400 font-semibold">{form6aResult.assigned_polling_station}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Constituency:</span>
                      <span className="text-slate-200">{form6aResult.registered_constituency}</span>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-400">
                    <div className="font-semibold text-slate-300 mb-1">In-Person Polling Requirement:</div>
                    {form6aResult.voting_requirement}
                  </div>

                  <Link
                    href="/map"
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 text-xs"
                  >
                    View Constituency on Map
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center space-y-3">
                  <FileCheck2 className="w-10 h-10 text-slate-600 mx-auto" />
                  <p className="text-sm text-slate-300 font-medium">Form 6A Status Preview</p>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    Submit the simulated enrollment form on the left to inspect the generated reference number, pseudonymized identifier, and home polling station allocation.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Mode B: Consular Research Lab */}
      {activeTab === "mode_b" && (
        <div className="space-y-6">
          <div className="bg-indigo-500/10 border border-indigo-500/30 p-4 rounded-xl flex items-start gap-3">
            <Shield className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-300 space-y-1">
              <span className="font-bold text-indigo-400">SecureVOTE Academic Research Prototype — Consular Polling Protocol:</span>
              <p>
                Mode B is an academic research demonstration exploring how overseas electors could securely cast verifiable ballots without traveling internationally.
                It models dual-custody authorization by two independent consular officials, cryptographic blind session tokens, and tamper-evident diplomatic audit chains.
              </p>
              <div className="bg-rose-950/40 border border-rose-500/40 rounded p-2 mt-2 space-y-0.5 text-[11px] text-rose-300 font-mono">
                <div className="font-bold text-rose-400">RESEARCH PROPOSAL — NOT CURRENT INDIAN ELECTION PROCEDURE</div>
                <div>• NOT STATUTORY • ACADEMIC DEMONSTRATION ONLY</div>
                <div>• Not recognized by the Election Commission of India — no actual vote is cast or registered</div>
                <div>• USE SYNTHETIC TEST DATA ONLY. DO NOT ENTER REAL PASSPORT INFORMATION.</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Consular Simulation Controls */}
            <div className="lg:col-span-6 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Building2 className="w-5 h-5 text-indigo-400" />
                Consular Booth Dual-Control Simulator
              </h2>

              <div className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1">Designated Indian Diplomatic Mission / Consulate</label>
                  <select
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500"
                    value={consulateCity}
                    onChange={(e) => setConsulateCity(e.target.value)}
                  >
                    <option value="San Francisco">Consulate General of India, San Francisco (USA)</option>
                    <option value="New York">Consulate General of India, New York (USA)</option>
                    <option value="London">High Commission of India, London (UK)</option>
                    <option value="Dubai">Consulate General of India, Dubai (UAE)</option>
                    <option value="Singapore">High Commission of India, Singapore</option>
                  </select>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
                  <div className="text-slate-300 font-semibold flex items-center gap-2">
                    <KeyRound className="w-4 h-4 text-indigo-400" />
                    Dual-Control Custody Key Protocol
                  </div>
                  <p className="text-slate-400 text-[11px]">
                    In Mode B, session authorization requires physical sign-off from two separate consular officials: the Presiding Diplomatic Officer and an independent Observer. Both must enter their cryptographic keys before the EVM twin terminal enables the overseas ballot interface.
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-400">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 text-emerald-400">
                      Officer 1: KEY-DIP-AUTH-88A
                    </div>
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 text-emerald-400">
                      Officer 2: KEY-DIP-OBSV-42C
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleConsularSimulate}
                  disabled={simulatingConsular}
                  className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2 text-sm disabled:opacity-50"
                >
                  {simulatingConsular ? "Simulating Protocol..." : "Generate Consular Authorization Token"}
                </button>
              </div>
            </div>

            {/* Consular Result Display */}
            <div className="lg:col-span-6 space-y-6">
              {consularResult ? (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <span className="text-xs font-mono text-indigo-400 font-bold">RESEARCH PROPOSAL RECEIPT</span>
                    <span className="bg-indigo-500/20 text-indigo-300 text-[10px] font-mono px-2 py-0.5 rounded border border-indigo-500/30">
                      {consularResult.tamper_evident_seal_id}
                    </span>
                  </div>

                  <div className="space-y-3 text-xs">
                    <div>
                      <span className="text-slate-500">Mission Location:</span>
                      <p className="text-slate-200 font-semibold">{consularResult.consulate}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Session Authorization Token:</span>
                      <p className="font-mono text-amber-400 font-bold break-all">{consularResult.session_token}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Diplomatic Custody Hash:</span>
                      <p className="font-mono text-slate-400 text-[10px] break-all">{consularResult.diplomatic_custody_hash}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Dual Custody Witnesses:</span>
                      <div className="text-emerald-400 font-mono text-[11px] mt-1 space-y-0.5">
                        {consularResult.dual_custody_officers?.map((o: string, idx: number) => (
                          <div key={idx}>&bull; {o}</div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-amber-400 font-mono">
                    {consularResult.advisory_notice}
                  </div>

                  <Link
                    href="/evm"
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2 text-xs"
                  >
                    Proceed to Simulated Ballot Terminal
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center space-y-3">
                  <Lock className="w-10 h-10 text-slate-600 mx-auto" />
                  <p className="text-sm text-slate-300 font-medium">Consular Session Pending</p>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    Select a diplomatic mission and simulate the dual-control sign-off protocol to generate the cryptographic session authorization token.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
