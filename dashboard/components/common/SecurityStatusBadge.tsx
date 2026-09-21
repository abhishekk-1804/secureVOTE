"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, Clock, Shield, Info } from "lucide-react";
import clsx from "clsx";

export type SecurityState = "VERIFIED" | "WARNING" | "PILOT" | "STANDBY" | "READY" | "PENDING";

export interface SecurityStatusBadgeProps {
  status: SecurityState | string;
  size?: "sm" | "md" | "lg";
  className?: string;
  showIcon?: boolean;
}

const STATUS_CONFIG: Record<string, {
  label: string;
  sublabel: string;
  icon: React.ComponentType<{ className?: string }>;
  badgeClass: string;
  textClass: string;
}> = {
  VERIFIED: {
    label: "VERIFIED",
    sublabel: "Cryptographically Verified",
    icon: CheckCircle2,
    badgeClass: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    textClass: "text-emerald-400",
  },
  WARNING: {
    label: "WARNING",
    sublabel: "Audit Anomaly Detected",
    icon: AlertTriangle,
    badgeClass: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    textClass: "text-amber-400",
  },
  PILOT: {
    label: "PILOT ACTIVE",
    sublabel: "Karnataka Simulation",
    icon: Shield,
    badgeClass: "bg-blue-500/10 border-blue-500/30 text-blue-400",
    textClass: "text-blue-400",
  },
  READY: {
    label: "READY",
    sublabel: "Reference Baseline",
    icon: Clock,
    badgeClass: "bg-slate-800 border-slate-700 text-slate-300",
    textClass: "text-slate-300",
  },
  STANDBY: {
    label: "STANDBY",
    sublabel: "Awaiting Schedule",
    icon: Clock,
    badgeClass: "bg-slate-800 border-slate-700 text-slate-400",
    textClass: "text-slate-400",
  },
  PENDING: {
    label: "PENDING",
    sublabel: "Verification In Flight",
    icon: Info,
    badgeClass: "bg-purple-500/10 border-purple-500/30 text-purple-400",
    textClass: "text-purple-400",
  },
};

export function SecurityStatusBadge({
  status,
  size = "md",
  className,
  showIcon = true,
}: SecurityStatusBadgeProps) {
  const normalized = (status || "READY").toUpperCase();
  const config = STATUS_CONFIG[normalized] || STATUS_CONFIG.READY;
  const Icon = config.icon;

  const sizeClasses = {
    sm: "text-[10px] px-2 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5",
    lg: "text-sm px-3 py-1.5 gap-2 font-medium",
  };

  const iconSizes = {
    sm: "w-3 h-3",
    md: "w-3.5 h-3.5",
    lg: "w-4 h-4",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border font-mono font-semibold tracking-wider uppercase",
        config.badgeClass,
        sizeClasses[size],
        className
      )}
      title={config.sublabel}
      aria-label={`${config.label}: ${config.sublabel}`}
    >
      {showIcon && <Icon className={clsx("shrink-0", iconSizes[size])} aria-hidden="true" />}
      <span>{config.label}</span>
    </span>
  );
}
