"use client";

import React, { useState } from "react";
import { useElection } from "@/context/ElectionContext";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Users,
  Shield,
  FileCheck,
  CheckCircle2,
  Clock,
  AlertCircle,
  Plus,
  Info,
} from "lucide-react";

interface PartyProfile {
  id: string;
  name: string;
  shortName: string;
  symbol: string;
  nationalRegistrationId: string;
  candidatesCount: number;
  complianceStatus: "VERIFIED" | "PENDING" | "REVIEW";
}

const DEMO_PARTIES: PartyProfile[] = [
  {
    id: "P01",
    name: "Democratic Reform Party",
    shortName: "DRP",
    symbol: "ðŸ˜",
    nationalRegistrationId: "PR-2026-DRP",
    candidatesCount: 1,
    complianceStatus: "VERIFIED",
  },
  {
    id: "P02",
    name: "People's Progress Alliance",
    shortName: "PPA",
    symbol: "ðŸŒ¾",
    nationalRegistrationId: "PR-2026-PPA",
    candidatesCount: 1,
    complianceStatus: "VERIFIED",
  },
  {
    id: "P03",
    name: "National Development Front",
    shortName: "NDF",
    symbol: "â˜€ï¸",
    nationalRegistrationId: "PR-2026-NDF",
    candidatesCount: 1,
    complianceStatus: "VERIFIED",
  },
  {
    id: "P04",
    name: "Citizens United Movement",
    shortName: "CUM",
    symbol: "âš–ï¸",
    nationalRegistrationId: "PR-2026-CUM",
    candidatesCount: 1,
    complianceStatus: "VERIFIED",
  },
];

export default function CandidatePartyServicesPage() {
  const { selectedElection } = useElection();
  const [parties] = useState<PartyProfile[]>(DEMO_PARTIES);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-400" />
            Candidate & Party Services
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Party registrations, candidate nominations, symbol allocations, and compliance checklists
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="neutral">PROTOTYPE SERVICE</Badge>
        </div>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 flex items-start gap-2">
        <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-white">Simulated Party Registry:</span> Synthetic party profiles and nomination data for educational prototype validation. Does not represent actual legal political party registration.
        </div>
      </div>

      {/* Parties List */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-bold text-white">Registered Political Parties</h2>
          <span className="text-xs text-slate-400">{parties.length} Registered</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {parties.map((party) => (
            <div
              key={party.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-xl">
                    {party.symbol}
                  </span>
                  <div>
                    <h3 className="text-sm font-bold text-white">{party.name}</h3>
                    <p className="text-xs text-slate-400 font-mono">
                      {party.shortName} â€¢ {party.nationalRegistrationId}
                    </p>
                  </div>
                </div>

                <Badge variant={party.complianceStatus === "VERIFIED" ? "success" : "warning"}>
                  {party.complianceStatus}
                </Badge>
              </div>

              <div className="border-t border-slate-800/80 pt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-slate-500 block">Nominees Fielded</span>
                  <span className="text-slate-200 font-semibold">{party.candidatesCount} Candidate</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Nomination Scrutiny</span>
                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Approved
                  </span>
                </div>
              </div>

              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60 text-[11px] text-slate-400 space-y-1">
                <span className="font-semibold text-slate-300 block">Compliance Checklist:</span>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>Affidavit on Criminal Antecedents Filed</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>Financial Asset Disclosures Verified</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>EVM Symbol Assignment Frozen</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
