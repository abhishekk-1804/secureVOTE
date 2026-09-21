"use client";

import React, { useState } from "react";
import {
  Vote,
  Lock,
  FileCheck2,
  ScrollText,
  Calculator,
  Users,
  ShieldCheck,
  CheckCircle2,
  ChevronRight,
  Info,
} from "lucide-react";
import clsx from "clsx";

export interface PipelineStage {
  id: number;
  title: string;
  shortDesc: string;
  math: string;
  status: "COMPLETED" | "ACTIVE" | "PENDING";
  icon: React.ComponentType<{ className?: string }>;
}

const STAGES: PipelineStage[] = [
  {
    id: 1,
    title: "Voter Choice & Balloting",
    shortDesc: "Rule 49B NOTA support, CU/BU button press, 7s VVPAT viewing window.",
    math: "v in {0, 1}^K, sum(v) = 1",
    status: "COMPLETED",
    icon: Vote,
  },
  {
    id: 2,
    title: "Additive ElGamal Encryption",
    shortDesc: "NIST P-256 (secp256r1) elliptic curve. Candidate slots encrypted under joint PK.",
    math: "C = (r*G, M + r*Y)",
    status: "COMPLETED",
    icon: Lock,
  },
  {
    id: 3,
    title: "CDS94 Disjunctive ZKP",
    shortDesc: "Fiat-Shamir non-interactive proof that each ciphertext encrypts 0 or 1 without revealing voter intent.",
    math: "c = c_0 + c_1 mod q",
    status: "COMPLETED",
    icon: FileCheck2,
  },
  {
    id: 4,
    title: "Append-Only Audit Chain",
    shortDesc: "Monotonic sequence numbers, previous-hash binding, tamper-evident audit logs.",
    math: "H_i = SHA256(H_{i-1} || e_i)",
    status: "COMPLETED",
    icon: ScrollText,
  },
  {
    id: 5,
    title: "Homomorphic Aggregation",
    shortDesc: "Ballots multiplied coordinate-wise without decryption; tally equals sum of votes.",
    math: "Prod(C_i) = Enc(sum(v_i))",
    status: "COMPLETED",
    icon: Calculator,
  },
  {
    id: 6,
    title: "2-of-3 GJKR DKG",
    shortDesc: "Pedersen VSS + Feldman commitments. Joint PK derived with zero trusted dealer.",
    math: "Y = sum(A_{j,0}) * G",
    status: "COMPLETED",
    icon: Users,
  },
  {
    id: 7,
    title: "Verifiable Partial Decryption",
    shortDesc: "Trustees generate partial decryption shares with Chaum-Pedersen DLEQ proofs.",
    math: "D_i = s_i * C_1; DLEQ(G, Y_i, C_1, D_i)",
    status: "COMPLETED",
    icon: ShieldCheck,
  },
  {
    id: 8,
    title: "Standalone Verification",
    shortDesc: "Deterministic offline replay checking 11 mathematical checkpoints independently.",
    math: "Verify(Tally, Proofs, Log) -> Valid",
    status: "COMPLETED",
    icon: CheckCircle2,
  },
];

export function CryptoPipeline({ className }: { className?: string }) {
  const [selectedStage, setSelectedStage] = useState<PipelineStage>(STAGES[0]);

  return (
    <div className={clsx("bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl", className)}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            End-to-End Cryptographic Verification Pipeline
          </h3>
          <p className="text-xs text-slate-400">
            From ballot casting to 2-of-3 threshold tallying and offline mathematical verification.
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold self-start sm:self-auto">
          ALL 8 STAGES ACTIVE
        </span>
      </div>

      {/* Horizontal Stage Tracker */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 mb-6">
        {STAGES.map((stage) => {
          const Icon = stage.icon;
          const isSelected = selectedStage.id === stage.id;

          return (
            <button
              key={stage.id}
              onClick={() => setSelectedStage(stage)}
              className={clsx(
                "p-3 rounded-lg border text-left transition-all flex flex-col justify-between min-h-[90px]",
                isSelected
                  ? "bg-emerald-500/15 border-emerald-500/50 text-emerald-300 ring-1 ring-emerald-500/30"
                  : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
              )}
            >
              <div className="flex items-center justify-between w-full">
                <span className="text-[10px] font-mono font-bold text-slate-500">
                  0{stage.id}
                </span>
                <Icon className={clsx("w-4 h-4", isSelected ? "text-emerald-400" : "text-slate-500")} />
              </div>
              <div className="text-xs font-bold leading-tight mt-2 text-white truncate">
                {stage.title}
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected Stage Explanation Drawer */}
      <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-4 grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
        <div className="md:col-span-8 space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-emerald-400 font-bold">
              Stage 0{selectedStage.id}:
            </span>
            <h4 className="text-sm font-bold text-white">{selectedStage.title}</h4>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {selectedStage.shortDesc}
          </p>
        </div>

        <div className="md:col-span-4 bg-slate-900 border border-slate-800 p-3 rounded font-mono text-xs text-center space-y-1">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
            Mathematical Invariant
          </span>
          <div className="text-emerald-300 font-semibold break-all text-[11px]">
            {selectedStage.math}
          </div>
        </div>
      </div>
    </div>
  );
}
