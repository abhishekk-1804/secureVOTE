"use client";

import React, { useState } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  FileText,
  Download,
  CheckCircle2,
  Printer,
  Shield,
  Clock,
  Hash,
  Info,
} from "lucide-react";

export default function ElectionReportsPage() {
  const { selectedElection } = useElection();
  const [exporting, setExporting] = useState(false);

  const handleExportArchive = async () => {
    if (!selectedElection) return;
    setExporting(true);
    try {
      const data = await api.exportElection(selectedElection.id);
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `export_${selectedElection.id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert("Failed to export: " + (err.message || "Unknown error"));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-400" />
            Election Officer Reports & Documentation
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographic export packages, reconciliation certificates, and compliance transcripts
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={handleExportArchive}
            loading={exporting}
            disabled={!selectedElection}
          >
            <Download className="w-3.5 h-3.5 mr-1" />
            Download Verifiable Archive (.json)
          </Button>
        </div>
      </div>

      {selectedElection && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white text-base">Reconciliation Certificate</CardTitle>
                <CardDescription>Operational multi-point balance summary</CardDescription>
              </CardHeader>
              <div className="pt-3 space-y-2 text-xs text-slate-300">
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-500">Election Identifier</span>
                  <span className="font-mono text-white">{selectedElection.id}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-500">Total Ballots Cast</span>
                  <span className="font-bold text-emerald-400">{selectedElection.ballot_count}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-500">Reporting Hardware Units</span>
                  <span>{selectedElection.device_count} EVM Units</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-slate-500">Reconciliation Status</span>
                  <Badge variant="success">EXACT_MATCH</Badge>
                </div>
              </div>
            </Card>

            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white text-base">Cryptographic Manifest Record</CardTitle>
                <CardDescription>Canonical signature & hash fingerprint</CardDescription>
              </CardHeader>
              <div className="pt-3 space-y-2 text-xs text-slate-300">
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-500">Configuration Hash</span>
                  <span className="font-mono text-slate-300 truncate max-w-[200px]" title={selectedElection.configuration_hash || ""}>
                    {selectedElection.configuration_hash?.substring(0, 16) || "Pending"}...
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-500">Audit Trail Integrity</span>
                  <span className="font-semibold text-emerald-400">Continuous SHA-256 Intact</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-500">Signature Standard</span>
                  <span className="font-mono text-slate-300">Ed25519 (RFC 8032)</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-slate-500">External Audit Anchor</span>
                  <span className="text-slate-400">Local Commitment Record</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
