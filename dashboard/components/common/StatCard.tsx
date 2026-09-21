"use client";

import React from "react";
import { LucideIcon } from "lucide-react";
import clsx from "clsx";

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  variant?: "default" | "success" | "warning" | "info" | "purple";
  badge?: string;
  onClick?: () => void;
  className?: string;
}

const VARIANT_STYLES = {
  default: {
    bg: "bg-slate-900 border-slate-800 text-slate-100",
    iconBg: "bg-slate-800 text-slate-400",
    badge: "bg-slate-800 text-slate-300 border-slate-700",
  },
  success: {
    bg: "bg-slate-900 border-emerald-500/30 text-emerald-100",
    iconBg: "bg-emerald-500/10 text-emerald-400",
    badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  },
  warning: {
    bg: "bg-slate-900 border-amber-500/30 text-amber-100",
    iconBg: "bg-amber-500/10 text-amber-400",
    badge: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  },
  info: {
    bg: "bg-slate-900 border-blue-500/30 text-blue-100",
    iconBg: "bg-blue-500/10 text-blue-400",
    badge: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  },
  purple: {
    bg: "bg-slate-900 border-purple-500/30 text-purple-100",
    iconBg: "bg-purple-500/10 text-purple-400",
    badge: "bg-purple-500/20 text-purple-300 border-purple-500/40",
  },
};

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
  badge,
  onClick,
  className,
}: StatCardProps) {
  const styles = VARIANT_STYLES[variant];

  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === "Enter" && onClick() : undefined}
      className={clsx(
        "p-5 rounded-xl border shadow-lg transition-all relative overflow-hidden",
        styles.bg,
        onClick && "cursor-pointer hover:scale-[1.01] hover:border-slate-700 active:scale-[0.99]",
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase truncate">
            {title}
          </p>
          <div className="text-2xl lg:text-3xl font-bold font-mono tracking-tight text-white">
            {value}
          </div>
          {subtitle && (
            <p className="text-xs text-slate-400 leading-snug mt-1">
              {subtitle}
            </p>
          )}
        </div>

        {Icon && (
          <div className={clsx("p-3 rounded-lg shrink-0", styles.iconBg)}>
            <Icon className="w-5 h-5" aria-hidden="true" />
          </div>
        )}
      </div>

      {badge && (
        <div className="mt-3 pt-3 border-t border-slate-800/60 flex items-center justify-between">
          <span
            className={clsx(
              "text-[10px] font-mono px-2 py-0.5 rounded border uppercase tracking-wider",
              styles.badge
            )}
          >
            {badge}
          </span>
        </div>
      )}
    </div>
  );
}
