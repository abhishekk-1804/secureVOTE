"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { ElectionResponse, ElectionExportResponse } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  FileCheck,
  ShieldCheck,
  ShieldAlert,
  Upload,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  Hash,
  Calculator,
  Key,
} from "lucide-react";
import { runCryptographicVerification, VerificationCheckResult } from "@/lib/verifier-crypto";

export default function IndependentVerificationPage() {
  const { token } = useAuth();
  const [elections, setElections] = useState<ElectionResponse[]>([]);
  const [selectedElectionId, setSelectedElectionId] = useState<string>("");
  const [loadingElections, setLoadingElections] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [exportPackage, setExportPackage] = useState<ElectionExportResponse | null>(null);
  const [checkpoints, setCheckpoints] = useState<VerificationCheckResult[]>([]);
  const [recountedStats, setRecountedStats] = useState<{
    ballots: number;
    candidatesCount: number;
    devicesCount: number;
    auditEntries: number;
    reconciliationDrift: number;
  } | null>(null);
  const [mismatches, setMismatches] = useState<string[]>([]);
  const [overallStatus, setOverallStatus] = useState<"PASSED" | "FAILED" | null>(null);
  const [customFileLoaded, setCustomFileLoaded] = useState(false);

  useEffect(() => {
    async function loadElectionsList() {
      try {
        let list: any[] = [];
        if (token) {
          try {
            list = await api.getElections(token);
          } catch {}
        }
        if (list.length === 0) {
          const publicData = await api.getTransparencyElections();
          list = publicData.map(e => ({
            id: e.election_id,
            name: e.election_name,
            title: e.election_name,
            state: e.state,
            total_ballots: e.total_ballots,
            device_count: e.device_count,
          } as any));
        }
        setElections(list);
        if (list.length > 0) {
          setSelectedElectionId(prev => prev || list[0].id);
        }
      } catch {
        // Handle gracefully if backend is offline
      } finally {
        setLoadingElections(false);
      }
    }
    loadElectionsList();
  }, [token]);

  const runVerificationOnData = async (data: ElectionExportResponse) => {
    setVerifying(true);
    setOverallStatus(null);
    setMismatches([]);
    setExportPackage(data);

    // Give visual progression
    await new Promise((resolve) => setTimeout(resolve, 400));

    try {
      const signatureVerifier = async (payload: any, signature: string, publicKey?: string) => {
        try {
          const res = await api.verifySignature(payload, signature, publicKey);
          return Boolean(res.valid);
        } catch {
          return false;
        }
      };

      const report = await runCryptographicVerification(data, signatureVerifier);
      setCheckpoints(report.checkpoints);
      setRecountedStats(report.recountedStats);
      setMismatches(report.mismatches);
      setOverallStatus(report.valid ? "PASSED" : "FAILED");
    } catch (err: any) {
      alert("Verification processing error: " + (err.message || "Unknown error"));
      setOverallStatus("FAILED");
    } finally {
      setVerifying(false);
    }
  };

  const [isTamperDemo, setIsTamperDemo] = useState(false);

  const handleFetchAndVerify = async () => {
    if (!selectedElectionId) return;
    try {
      setVerifying(true);
      setIsTamperDemo(false);
      const data = await api.exportElection(selectedElectionId, token);
      setCustomFileLoaded(false);
      await runVerificationOnData(data);
    } catch (err: any) {
      alert("Failed to export election data: " + (err.message || "Unknown error"));
      setVerifying(false);
    }
  };

  const handleSimulateTamper = async () => {
    if (!selectedElectionId) return;
    try {
      setVerifying(true);
      let data = exportPackage;
      if (!data) {
        data = await api.exportElection(selectedElectionId, token);
      }
      // Create a cloned mutated package with a corrupted audit chain entry
      const mutated: ElectionExportResponse = JSON.parse(JSON.stringify(data));
      if (mutated.audit_log && mutated.audit_log.length > 1) {
        mutated.audit_log[1].previous_hash = "deadbeef00000000000000000000000000000000000000000000000000000000";
      } else if (mutated.ballots && mutated.ballots.length > 0) {
        mutated.ballots[0].ballot_hash = "ffffffff00000000000000000000000000000000000000000000000000000000";
      }
      setIsTamperDemo(true);
      await runVerificationOnData(mutated);
    } catch (err: any) {
      alert("Failed to run tamper simulation: " + (err.message || "Unknown error"));
      setVerifying(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const json = JSON.parse(text);
        setCustomFileLoaded(true);
        await runVerificationOnData(json);
      } catch (err) {
        alert("Invalid JSON election archive file.");
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="text-center space-y-3 max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full border border-emerald-200">
          <FileCheck className="w-3.5 h-3.5" />
          Independent Machine Verifier
        </div>
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
          Third-Party Election Verifier
        </h1>
        <p className="text-slate-600 text-sm">
          Independently audits raw exported election records without trusting the database, backend ORM, or dashboard.
        </p>
      </div>

      {/* Trust Notice */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-700 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-slate-900">Zero-Trust Boundary</p>
          <p className="text-slate-600 leading-relaxed mt-0.5">
            This verifier independently recalculates all hash chains, tallies ballots from raw records, and proves reconciliation. It replicates the standalone verifier specification in <code>backend/standalone_verifier/verifier.py</code>.
          </p>
        </div>
      </div>

      {/* Control Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Select Verification Target</CardTitle>
          <CardDescription>
            Choose a live election to export and verify, or upload an exported JSON package
          </CardDescription>
        </CardHeader>
        <div className="pt-4 flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex items-center gap-3 w-full md:w-auto">
            <select
              value={selectedElectionId}
              onChange={(e) => setSelectedElectionId(e.target.value)}
              className="bg-white border border-slate-300 text-slate-800 text-xs rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 w-full md:w-64"
              disabled={loadingElections || verifying}
            >
              {elections.map((el) => (
                <option key={el.id} value={el.id}>
                  {el.id} - {el.title}
                </option>
              ))}
            </select>
            <Button
              variant="primary"
              size="sm"
              onClick={handleFetchAndVerify}
              loading={verifying}
              disabled={!selectedElectionId}
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              Fetch & Verify
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleSimulateTamper}
              loading={verifying}
              disabled={!selectedElectionId}
              className="border-rose-300 text-rose-700 hover:bg-rose-50"
              title="Demonstrate how deliberate hash chain mutation triggers verification failure"
            >
              <AlertTriangle className="w-3.5 h-3.5 mr-1 text-rose-600" />
              Simulate Mutation
            </Button>
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto justify-end">
            <label className="cursor-pointer inline-flex items-center justify-center gap-2 font-semibold rounded-lg transition-colors border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs px-3 py-2">
              <Upload className="w-3.5 h-3.5 text-slate-500" />
              Upload export.json
              <input
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleFileUpload}
                disabled={verifying}
              />
            </label>
          </div>
        </div>
      </Card>

      {/* Controlled Tamper Demonstration Evidence Banner */}
      {isTamperDemo && overallStatus === "FAILED" && (
        <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-xl text-xs text-amber-950 space-y-1 shadow-sm">
          <div className="font-bold flex items-center gap-1.5 text-amber-900">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            Demonstration Evidence: Cryptographic Tamper-Evidence In Action
          </div>
          <p className="leading-relaxed">
            The verifier detected a deliberate hash-chain mutation. In an append-only SHA-256 hash chain, altering any past entry invalidates the cryptographic continuity of all subsequent records. This demonstrates that silent historical mutations cannot occur undetected. Click <strong>Fetch &amp; Verify</strong> to re-verify the authentic live database record.
          </p>
        </div>
      )}

      {/* Recount Summary Banner (if verified) */}
      {overallStatus && recountedStats && (
        <div
          className={`p-5 rounded-xl border flex flex-col sm:flex-row items-center justify-between gap-4 ${
            overallStatus === "PASSED"
              ? "bg-emerald-50 border-emerald-200 text-emerald-950"
              : "bg-rose-50 border-rose-200 text-rose-950"
          }`}
        >
          <div className="flex items-center gap-3">
            {overallStatus === "PASSED" ? (
              <CheckCircle2 className="w-8 h-8 text-emerald-600 shrink-0" />
            ) : (
              <XCircle className="w-8 h-8 text-rose-600 shrink-0" />
            )}
            <div>
              <h2 className="text-lg font-bold">
                {overallStatus === "PASSED"
                  ? "INDEPENDENT VERIFICATION: PASSED"
                  : "INDEPENDENT VERIFICATION: FAILED"}
              </h2>
              <p className="text-xs opacity-80">
                {overallStatus === "PASSED"
                  ? "All verified independent mathematical checks succeeded with zero reconciliation drift."
                  : "Integrity check failure detected in one or more checkpoints."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono font-semibold">
            <div className="text-center">
              <span className="text-[10px] block opacity-70">Recounted</span>
              <span>{recountedStats.ballots} Ballots</span>
            </div>
            <div className="text-center">
              <span className="text-[10px] block opacity-70">Audit Events</span>
              <span>{recountedStats.auditEntries}</span>
            </div>
            <div className="text-center">
              <span className="text-[10px] block opacity-70">Drift</span>
              <span>{recountedStats.reconciliationDrift}</span>
            </div>
          </div>
        </div>
      )}

      {/* Explicit Cryptographic Mismatches List */}
      {mismatches.length > 0 && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-900 space-y-2 shadow-sm">
          <div className="font-bold flex items-center gap-1.5 text-rose-800">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            Cryptographic Mismatches / Violations Detected ({mismatches.length})
          </div>
          <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-rose-700">
            {mismatches.map((m, idx) => (
              <li key={idx}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Verification Checkpoints List */}
      {checkpoints.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-base font-bold text-slate-900">
            Independent Verification Checkpoints
          </h3>
          <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl bg-white overflow-hidden shadow-sm">
            {checkpoints.map((cp) => (
              <div key={cp.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-slate-900">
                      {cp.name}
                    </span>
                    <Badge
                      variant={
                        cp.status === "PASSED"
                          ? "success"
                          : cp.status === "FAILED"
                          ? "danger"
                          : "warning"
                      }
                    >
                      {cp.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500">{cp.description}</p>
                  {cp.details && (
                    <p className="text-xs font-mono text-slate-700 bg-slate-50 px-2 py-1 rounded inline-block">
                      {cp.details}
                    </p>
                  )}
                </div>

                <div className="shrink-0">
                  {cp.status === "PASSED" && (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  )}
                  {cp.status === "FAILED" && (
                    <XCircle className="w-5 h-5 text-rose-500" />
                  )}
                  {(cp.status === "UNCHECKED" || (cp.status as any) === "PENDING") && (
                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
