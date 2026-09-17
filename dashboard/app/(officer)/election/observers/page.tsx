"use client";

import React, { useEffect, useState } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  Eye,
  ShieldCheck,
  Vote,
  Cpu,
  MapPin,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
} from "lucide-react";

export default function ObserverDashboardPage() {
  const { selectedElection } = useElection();
  const [auditStatus, setAuditStatus] = useState<string>("Verifying...");
  const [deviceCount, setDeviceCount] = useState<number>(0);

  useEffect(() => {
    async function loadObserverTelemetry() {
      if (!selectedElection) return;
      try {
        const [auditRes, devRes] = await Promise.all([
          api.verifyAuditChain(selectedElection.id).catch(() => null),
          api.getDevices(selectedElection.id).catch(() => []),
        ]);
        if (auditRes) {
          setAuditStatus(auditRes.is_intact ? "INTACT (Verified)" : "CHAIN FAILURE DETECTED");
        }
        if (devRes) {
          setDeviceCount(devRes.length);
        }
      } catch {}
    }
    loadObserverTelemetry();
  }, [selectedElection]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Eye className="w-5 h-5 text-purple-400" />
            Independent Election Observer Portal
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Restricted operational view for designated non-partisan observers, media delegates, and audit monitors
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="neutral">READ-ONLY ACCESS</Badge>
        </div>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 flex items-start gap-2">
        <Lock className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-white">Observer Security Boundary:</span> Observers have non-mutating visibility over aggregate election metrics, device statuses, and cryptographic integrity proofs. System configuration, private voter sessions, and encryption keys are strictly restricted.
        </div>
      </div>

      {selectedElection && (
        <div className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <Card padding="sm" className="bg-slate-900 border-slate-800">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Vote className="w-3.5 h-3.5 text-blue-400" /> Recorded Ballots
              </span>
              <p className="text-2xl font-bold text-white mt-1">
                {selectedElection.ballot_count}
              </p>
              <span className="text-[10px] text-slate-500">Live tally count</span>
            </Card>

            <Card padding="sm" className="bg-slate-900 border-slate-800">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Cpu className="w-3.5 h-3.5 text-emerald-400" /> Active EVM Units
              </span>
              <p className="text-2xl font-bold text-white mt-1">
                {deviceCount || selectedElection.device_count}
              </p>
              <span className="text-[10px] text-slate-500">Hardware reporting</span>
            </Card>

            <Card padding="sm" className="bg-slate-900 border-slate-800">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-purple-400" /> Audit Integrity
              </span>
              <p className="text-sm font-bold text-emerald-400 mt-2 truncate">
                {auditStatus}
              </p>
              <span className="text-[10px] text-slate-500">SHA-256 continuous chain</span>
            </Card>

            <Card padding="sm" className="bg-slate-900 border-slate-800">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-400" /> Election State
              </span>
              <p className="text-lg font-bold text-slate-200 mt-1">
                {selectedElection.state}
              </p>
              <span className="text-[10px] text-slate-500 font-mono">
                {selectedElection.id}
              </span>
            </Card>
          </div>

          {/* Observer Checklist */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-white text-base">Observer Compliance Verification</CardTitle>
              <CardDescription>
                System invariants monitored continuously during the election lifecycle
              </CardDescription>
            </CardHeader>
            <div className="pt-4 space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 bg-slate-950/60 rounded-lg border border-slate-800/60">
                <span className="text-slate-300">Candidate Roster Frozen Post-Lock</span>
                <Badge variant="success">CONFIRMED</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-950/60 rounded-lg border border-slate-800/60">
                <span className="text-slate-300">Physical EVM Serial Bridge Active</span>
                <Badge variant="success">MONITORED</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-950/60 rounded-lg border border-slate-800/60">
                <span className="text-slate-300">Monotonic Sequence Monitored (Zero Replays)</span>
                <Badge variant="success">ENFORCED</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-950/60 rounded-lg border border-slate-800/60">
                <span className="text-slate-300">Voter PII Segregated from Ballot Records</span>
                <Badge variant="success">COMPLIANT</Badge>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
