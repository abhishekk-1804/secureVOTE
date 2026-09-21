"use client";

import React from "react";
import { KeyRound, ShieldCheck, CheckCircle2, Lock, ShieldAlert } from "lucide-react";
import clsx from "clsx";

export interface TrusteeCardProps {
  index: number;
  name: string;
  role: string;
  verificationKeyFingerprint: string;
  commitmentHash: string;
  isQual: boolean;
  hasSubmittedShare: boolean;
  status?: "ONLINE" | "STANDBY" | "OFFLINE";
  className?: string;
}

export function TrusteeCard({
  index,
  name,
  role,
  verificationKeyFingerprint,
  commitmentHash,
  isQual,
  hasSubmittedShare,
  status = "ONLINE",
  className,
}: TrusteeCardProps) {
  return (
    <div
      className={clsx(
        "p-5 rounded-xl border bg-slate-900 shadow-md relative overflow-hidden transition-all",
        isQual ? "border-slate-800" : "border-rose-500/30",
        className
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-mono font-bold text-sm">
            T{index}
          </div>
          <div>
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              {name}
              {isQual && (
                <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.2 rounded font-semibold">
                  QUAL
                </span>
              )}
            </h4>
            <p className="text-xs text-slate-400">{role}</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs font-mono">
          <span
            className={clsx(
              "w-2 h-2 rounded-full",
              status === "ONLINE" ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
            )}
          />
          <span className="text-slate-300 text-[11px] font-semibold">{status}</span>
        </div>
      </div>

      <div className="space-y-2 mt-4 text-xs font-mono">
        <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 space-y-1">
          <div className="text-[10px] text-slate-500 uppercase flex items-center justify-between">
            <span>Public Verification Key $Y_{index}$</span>
            <KeyRound className="w-3 h-3 text-slate-500" />
          </div>
          <div className="text-slate-300 text-[11px] break-all select-all font-mono">
            {verificationKeyFingerprint}
          </div>
        </div>

        <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 space-y-1">
          <div className="text-[10px] text-slate-500 uppercase flex items-center justify-between">
            <span>Feldman VSS Commitment $C_{index}$</span>
            <Lock className="w-3 h-3 text-slate-500" />
          </div>
          <div className="text-slate-400 text-[11px] truncate font-mono">
            {commitmentHash}
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
          <ShieldCheck className="w-4 h-4" />
          <span>{hasSubmittedShare ? "Decryption Share Verified" : "Key Share Armed"}</span>
        </div>

        <div
          className="text-[10px] text-slate-500 font-mono"
          title="Security Guarantee: Secret share x_i is strictly isolated on the trustee security module"
        >
          $x_{index}$ strictly isolated
        </div>
      </div>
    </div>
  );
}
