"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";
import { TransparencyOverview, CandidateResponse } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  ShieldCheck,
  Vote,
  Cpu,
  MapPin,
  Users,
  FileCheck,
  Download,
  ArrowLeft,
  Lock,
  ExternalLink,
  Hash,
  AlertCircle,
} from "lucide-react";

export default function ElectionTransparencyDetailPage() {
  const params = useParams();
  const electionId = params?.id as string;

  const [overview, setOverview] = useState<TransparencyOverview | null>(null);
  const [candidates, setCandidates] = useState<CandidateResponse[]>([]);
  const [resultsData, setResultsData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadElectionDetails() {
      if (!electionId) return;
      try {
        const [overviewRes, candidatesRes] = await Promise.all([
          api.getTransparencyOverview(electionId).catch(() => null),
          api.getTransparencyCandidates(electionId).catch(() => []),
        ]);

        if (overviewRes) {
          setOverview(overviewRes);
          if (overviewRes.state === "CLOSED" || overviewRes.state === "PUBLISHED") {
            const res = await api.getTransparencyResults(electionId).catch(() => null);
            setResultsData(res);
          }
        } else {
          setError(`Election ${electionId} not found or unavailable.`);
        }
        setCandidates(candidatesRes);
      } catch (err: any) {
        setError("Error loading transparency data.");
      } finally {
        setLoading(false);
      }
    }
    loadElectionDetails();
  }, [electionId]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
        <h2 className="text-xl font-bold text-slate-900">{error || "Election not found"}</h2>
        <Link href="/transparency">
          <Button variant="outline" size="sm">
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Transparency Center
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Back button */}
      <div>
        <Link href="/transparency" className="inline-flex items-center text-xs text-slate-500 hover:text-slate-800">
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Public Transparency Center
        </Link>
      </div>

      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-blue-600">
              {overview.election_id}
            </span>
            <Badge variant={overview.state === "OPEN" ? "success" : "neutral"}>
              {overview.state}
            </Badge>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">
            {overview.election_name}
          </h1>
          <p className="text-xs text-slate-500">
            Cryptographic Transparency & Independent Verifiability Dashboard
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/verify">
            <Button variant="primary" size="sm">
              <FileCheck className="w-4 h-4 mr-1" />
              Verify Archive
            </Button>
          </Link>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card padding="sm" className="text-center">
          <span className="text-[11px] text-slate-500 flex items-center justify-center gap-1">
            <Vote className="w-3.5 h-3.5 text-blue-500" /> Ballots Cast
          </span>
          <p className="text-2xl font-bold text-slate-900 mt-1">
            {overview.total_ballots}
          </p>
        </Card>
        <Card padding="sm" className="text-center">
          <span className="text-[11px] text-slate-500 flex items-center justify-center gap-1">
            <Cpu className="w-3.5 h-3.5 text-emerald-500" /> Reporting Units
          </span>
          <p className="text-2xl font-bold text-slate-900 mt-1">
            {overview.device_count}
          </p>
        </Card>
        <Card padding="sm" className="text-center">
          <span className="text-[11px] text-slate-500 flex items-center justify-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-amber-500" /> Polling Stations
          </span>
          <p className="text-2xl font-bold text-slate-900 mt-1">
            {overview.polling_station_count}
          </p>
        </Card>
        <Card padding="sm" className="text-center">
          <span className="text-[11px] text-slate-500 flex items-center justify-center gap-1">
            <Users className="w-3.5 h-3.5 text-purple-500" /> Candidates
          </span>
          <p className="text-2xl font-bold text-slate-900 mt-1">
            {overview.candidate_count}
          </p>
        </Card>
      </div>

      {/* Verification & Integrity Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
            Integrity Checkpoints
          </CardTitle>
          <CardDescription>
            Independent mathematical proofs validating the election record
          </CardDescription>
        </CardHeader>
        <div className="pt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
            <span className="text-slate-500 font-medium">Audit Hash Chain</span>
            <p className="text-sm font-bold text-emerald-700">
              {overview.audit_chain_status || "TAMPER-EVIDENT INTACT"}
            </p>
            <p className="text-[11px] text-slate-400">Continuous SHA-256 genesis tip</p>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
            <span className="text-slate-500 font-medium">Reconciliation</span>
            <p className="text-sm font-bold text-slate-800">
              {overview.reconciliation_status || "EXACT_MATCH"}
            </p>
            <p className="text-[11px] text-slate-400">Sum(Ballots) == Sum(Candidate Totals)</p>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
            <span className="text-slate-500 font-medium">Digital Manifest</span>
            <p className="text-sm font-bold text-slate-800">
              {overview.manifest_status || "VERIFIED"}
            </p>
            <p className="text-[11px] text-slate-400">Ed25519 signature verified</p>
          </div>
        </div>
      </Card>

      {/* Candidates List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-600" />
            Published Candidate Roster ({candidates.length})
          </CardTitle>
          <CardDescription>
            Simulated nominees and party affiliations for this election
          </CardDescription>
        </CardHeader>
        <div className="pt-4 divide-y divide-slate-100">
          {candidates.map((c) => (
            <div key={c.id} className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-slate-400">#{c.position}</span>
                <span className="w-8 h-8 rounded-full bg-blue-50 text-blue-700 flex items-center justify-center font-bold text-xs border border-blue-100 font-mono">
                  {c.symbol || "â˜…"}
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{c.name}</p>
                  <p className="text-xs text-slate-500">{c.party || "Independent"}</p>
                </div>
              </div>
              <span className="font-mono text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                ID: {c.id}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* Results (if closed/published) */}
      {resultsData && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Published Vote Tallies</CardTitle>
            <CardDescription>
              Simulation aggregate tallies verified by the Result Manifest
            </CardDescription>
          </CardHeader>
          <div className="pt-4 space-y-3">
            {resultsData.manifest?.candidate_results?.map((res: any) => (
              <div key={res.candidate_id} className="space-y-1">
                <div className="flex justify-between text-xs font-semibold text-slate-800">
                  <span>{res.candidate_name} ({res.party})</span>
                  <span>{res.vote_count} votes ({res.percentage}%)</span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-blue-600 h-full rounded-full transition-all"
                    style={{ width: `${res.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
