"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api-client";
import { VoterResponse } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  User,
  ArrowLeft,
  CheckCircle2,
  Info,
  Vote,
} from "lucide-react";

function VoterProfileContent() {
  const searchParams = useSearchParams();
  const initialVoterId = searchParams?.get("voterId") || "VTR-00101";

  const [voterIdInput, setVoterIdInput] = useState(initialVoterId);
  const [profile, setProfile] = useState<VoterResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const lookupProfile = async (id: string) => {
    if (!id.trim()) return;
    setLoading(true);
    try {
      const data = await api.lookupVoter("EV-2026-001", id.trim());
      setProfile(data);
    } catch {
      // Fallback demo profile if backend lookup misses
      setProfile({
        id: "vtr-demo-1",
        election_id: "EV-2026-001",
        voter_id_number: id.trim(),
        name: "Aarav Sharma",
        date_of_birth: "1994-05-12",
        constituency: "North District",
        polling_station_id: "PS-001",
        eligibility_status: "ELIGIBLE",
        registration_status: "VERIFIED",
        has_voted: true,
        registered_at: "2026-03-01T10:00:00Z",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialVoterId) {
      lookupProfile(initialVoterId);
    }
  }, [initialVoterId]);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div>
        <Link href="/voter" className="inline-flex items-center text-xs text-slate-500 hover:text-slate-800">
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Voter Portal
        </Link>
      </div>

      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <User className="w-6 h-6 text-blue-600" />
          Simulated Voter Card & Profile
        </h1>
        <p className="text-xs text-slate-500">
          Digital verification slip and registration summary for simulated citizen profile.
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 flex items-start gap-2">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold">Simulated Identity:</span> Prototype research model only. This voter profile does not correspond to any actual government election document.
        </div>
      </div>

      {/* Lookup Bar */}
      <Card>
        <div className="flex gap-2">
          <Input
            placeholder="Enter Voter ID (e.g. VTR-00101)..."
            value={voterIdInput}
            onChange={(e) => setVoterIdInput(e.target.value)}
          />
          <Button
            size="sm"
            onClick={() => lookupProfile(voterIdInput)}
            loading={loading}
          >
            Lookup Profile
          </Button>
        </div>
      </Card>

      {/* Profile Card */}
      {profile && (
        <div className="bg-white border-2 border-slate-300 rounded-2xl p-6 shadow-sm space-y-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-blue-600 text-white text-[10px] font-bold px-3 py-1 rounded-bl-xl tracking-wider">
            DEMO VOTER ID
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400">
                <User className="w-8 h-8" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900">{profile.name}</h2>
                <p className="font-mono text-sm text-blue-600 font-semibold">
                  {profile.voter_id_number}
                </p>
              </div>
            </div>

            <div className="flex flex-col items-end gap-1">
              <Badge variant={profile.registration_status === "VERIFIED" ? "success" : "neutral"}>
                {profile.registration_status}
              </Badge>
              <span className="text-[11px] text-slate-500 font-mono">
                Election: {profile.election_id}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-slate-400 block font-medium">Date of Birth</span>
              <p className="text-slate-800 font-semibold mt-0.5">{profile.date_of_birth}</p>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Constituency</span>
              <p className="text-slate-800 font-semibold mt-0.5">{profile.constituency}</p>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Assigned Polling Station</span>
              <p className="text-slate-800 font-semibold mt-0.5">
                {profile.polling_station_id || "Polling Station PS-001"}
              </p>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Eligibility Simulation</span>
              <p className="text-emerald-700 font-semibold mt-0.5 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {profile.eligibility_status}
              </p>
            </div>
          </div>

          {/* Post-Vote Status Section */}
          <div className="border-t border-slate-100 pt-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              Voting Status
            </h3>
            {profile.has_voted ? (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-emerald-900 flex items-center gap-1.5 text-sm">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    VOTE RECORDED
                  </span>
                  <span className="font-mono text-emerald-800 text-[11px]">
                    Ballot Ref: #VOTE-{profile.voter_id_number.slice(-3)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] text-emerald-800/80 pt-1 border-t border-emerald-200/60">
                  <div>
                    <span className="opacity-70">Polling Device:</span> EVM-001
                  </div>
                  <div>
                    <span className="opacity-70">Election:</span> {profile.election_id}
                  </div>
                </div>
                <p className="text-[10px] text-emerald-700/80 italic mt-1">
                  Note: In compliance with ballot secrecy, your candidate selection is never recorded or displayed on this receipt.
                </p>
              </div>
            ) : (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs flex items-center justify-between">
                <div>
                  <p className="font-semibold text-slate-700">No ballot recorded for this session.</p>
                  <p className="text-[11px] text-slate-500">You may cast your vote when the polling station opens.</p>
                </div>
                <Link href="/evm">
                  <Button size="sm" variant="primary">
                    <Vote className="w-3.5 h-3.5 mr-1" />
                    Open EVM
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function VoterProfilePage() {
  return (
    <Suspense fallback={<div className="max-w-3xl mx-auto px-4 py-8 text-center text-xs text-slate-400">Loading Voter Profile...</div>}>
      <VoterProfileContent />
    </Suspense>
  );
}
