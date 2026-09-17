"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { TransparencyOverview } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  Eye,
  ShieldCheck,
  Vote,
  Cpu,
  MapPin,
  CheckCircle,
  ExternalLink,
  Info,
} from "lucide-react";

export default function TransparencyLandingPage() {
  const [elections, setElections] = useState<TransparencyOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getTransparencyElections();
        setElections(data);
      } catch (err: any) {
        setError("Unable to connect to transparency service");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="text-center space-y-3 max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-semibold rounded-full border border-blue-200">
          <Eye className="w-3.5 h-3.5" />
          Public Transparency Center
        </div>
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
          Open Election Transparency
        </h1>
        <p className="text-slate-600 text-sm">
          Real-time aggregate election telemetry, audit chain integrity status, and verifiable manifest publications.
        </p>
      </div>

      {/* Trust Notice Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 flex items-start gap-3">
        <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold">Civic Privacy & Integrity Guarantee</p>
          <p className="text-amber-800 leading-relaxed">
            All data exposed on this portal is strictly aggregate. Under no circumstances are individual voter identities, ballot choices, RFID UIDs, or private cryptographic keys recorded or displayed.
          </p>
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-64 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <Card className="text-center py-12">
          <p className="text-sm text-slate-600 mb-4">{error}</p>
          <Button onClick={() => window.location.reload()} variant="outline" size="sm">
            Retry Connection
          </Button>
        </Card>
      )}

      {/* Elections List */}
      {!loading && !error && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">Active & Published Elections</h2>
            <span className="text-xs text-slate-500 font-mono">{elections.length} Record(s)</span>
          </div>

          {elections.length === 0 ? (
            <Card className="text-center py-12">
              <p className="text-sm text-slate-500">No public election records currently published.</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {elections.map((election) => (
                <Card key={election.election_id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs font-mono font-semibold text-blue-600">
                          {election.election_id}
                        </span>
                        <CardTitle className="mt-1 text-slate-900">{election.election_name}</CardTitle>
                      </div>
                      <Badge variant={election.state === "OPEN" ? "success" : "neutral"}>
                        {election.state}
                      </Badge>
                    </div>
                  </CardHeader>

                  <div className="pt-4 space-y-4">
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        <span className="text-[11px] text-slate-500 flex items-center justify-center gap-1">
                          <Vote className="w-3 h-3 text-blue-500" /> Ballots
                        </span>
                        <p className="text-base font-bold text-slate-900 mt-0.5">
                          {election.total_ballots}
                        </p>
                      </div>
                      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        <span className="text-[11px] text-slate-500 flex items-center justify-center gap-1">
                          <Cpu className="w-3 h-3 text-emerald-500" /> EVMs
                        </span>
                        <p className="text-base font-bold text-slate-900 mt-0.5">
                          {election.device_count}
                        </p>
                      </div>
                      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        <span className="text-[11px] text-slate-500 flex items-center justify-center gap-1">
                          <MapPin className="w-3 h-3 text-amber-500" /> Stations
                        </span>
                        <p className="text-base font-bold text-slate-900 mt-0.5">
                          {election.polling_station_count}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2 border-t border-slate-100 pt-3 text-xs">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Audit Trail:</span>
                        <span className="font-medium text-emerald-700 flex items-center gap-1">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          {election.audit_chain_status || "INTACT"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Reconciliation:</span>
                        <span className="font-medium text-slate-700">
                          {election.reconciliation_status || "EXACT_MATCH"}
                        </span>
                      </div>
                    </div>

                    <Link
                      href={`/transparency/elections/${election.election_id}`}
                      className="block w-full"
                    >
                      <Button variant="outline" size="sm" className="w-full">
                        View Transparency Audit
                        <ExternalLink className="w-3.5 h-3.5 ml-1" />
                      </Button>
                    </Link>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
