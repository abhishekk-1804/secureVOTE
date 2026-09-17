"use client";

import React from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  Vote,
  ArrowLeft,
  Cpu,
  ShieldCheck,
  CheckCircle2,
  Lock,
  ExternalLink,
  Info,
} from "lucide-react";

export default function VoterVoteGatewayPage() {
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
          <Vote className="w-6 h-6 text-blue-600" />
          Digital EVM Voting Terminal
        </h1>
        <p className="text-xs text-slate-500">
          Experience the SecureVOTE electronic voting machine digital twin.
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-900 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold">Simulated Polling Environment:</span> The Digital EVM interacts with the real SecureVOTE backend using cryptographic session tokens and monotonic sequence replay protection, replicating the physical Arduino hardware.
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Cpu className="w-5 h-5 text-blue-600" />
            Voting Steps on the EVM Terminal
          </CardTitle>
          <CardDescription>
            Follow this standard sequence inside the digital twin terminal
          </CardDescription>
        </CardHeader>
        <div className="pt-4 space-y-4">
          <div className="flex gap-3 text-xs">
            <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center shrink-0">1</span>
            <div>
              <p className="font-semibold text-slate-900">Initialize Polling Session</p>
              <p className="text-slate-500">The officer authorizes a single-use session credential for your voter profile.</p>
            </div>
          </div>
          <div className="flex gap-3 text-xs">
            <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center shrink-0">2</span>
            <div>
              <p className="font-semibold text-slate-900">Select Your Candidate</p>
              <p className="text-slate-500">Touch the candidate button on the physical-style EVM faceplate.</p>
            </div>
          </div>
          <div className="flex gap-3 text-xs">
            <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center shrink-0">3</span>
            <div>
              <p className="font-semibold text-slate-900">Confirm and Cast Vote</p>
              <p className="text-slate-500">Press the green Confirm button. The backend validates sequence numbers and writes an immutable audit record.</p>
            </div>
          </div>
          <div className="flex gap-3 text-xs">
            <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center shrink-0">4</span>
            <div>
              <p className="font-semibold text-slate-900">VVPAT Slip Verification</p>
              <p className="text-slate-500">A visual verification slip confirms your vote was committed before resetting to READY.</p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
            <div className="text-xs text-slate-500">
              Ready to launch the digital twin terminal?
            </div>
            <Link href="/evm">
              <Button variant="primary">
                <Cpu className="w-4 h-4 mr-1.5" />
                Launch EVM Terminal
                <ExternalLink className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            </Link>
          </div>
        </div>
      </Card>
    </div>
  );
}
