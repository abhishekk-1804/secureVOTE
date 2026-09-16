import React from "react";
import clsx from "clsx";

interface StatusBadgeProps {
  status: string;
  isDemo?: boolean;
  className?: string;
}

export function StatusBadge({ status, isDemo, className }: StatusBadgeProps) {
  const s = status.toUpperCase();

  let colorClasses = "bg-gray-100 text-gray-800 border-gray-300";

  // State / status color logic
  if (["OPEN", "ACTIVE", "PASSED", "INTACT"].includes(s)) {
    colorClasses = "bg-emerald-50 text-emerald-700 border-emerald-300";
  } else if (["LOCKED", "CONFIGURED"].includes(s)) {
    colorClasses = "bg-blue-50 text-blue-700 border-blue-300";
  } else if (["SUSPENDED", "PAUSED", "WARNING"].includes(s)) {
    colorClasses = "bg-amber-50 text-amber-800 border-amber-300";
  } else if (
    [
      "REVOKED",
      "FAILED",
      "RECONCILIATION FAILURE",
      "BROKEN",
      "ERROR",
      "TAMPER_DETECTED",
    ].includes(s)
  ) {
    colorClasses = "bg-rose-50 text-rose-700 border-rose-300";
  } else if (["CLOSED", "PUBLISHED"].includes(s)) {
    colorClasses = "bg-purple-50 text-purple-700 border-purple-300";
  } else if (["ADMIN"].includes(s)) {
    colorClasses = "bg-indigo-50 text-indigo-700 border-indigo-300";
  } else if (["AUDITOR"].includes(s)) {
    colorClasses = "bg-teal-50 text-teal-700 border-teal-300";
  } else if (["OBSERVER"].includes(s)) {
    colorClasses = "bg-slate-100 text-slate-700 border-slate-300";
  }

  return (
    <div className={clsx("inline-flex items-center gap-1.5", className)}>
      <span
        className={clsx(
          "px-2.5 py-0.5 rounded-full text-xs font-semibold border inline-flex items-center tracking-wide",
          colorClasses
        )}
      >
        <span
          className={clsx(
            "w-1.5 h-1.5 rounded-full mr-1.5",
            ["OPEN", "ACTIVE", "PASSED", "INTACT"].includes(s)
              ? "bg-emerald-500 animate-pulse"
              : ["SUSPENDED", "PAUSED"].includes(s)
              ? "bg-amber-500"
              : ["REVOKED", "FAILED", "RECONCILIATION FAILURE", "BROKEN"].includes(s)
              ? "bg-rose-500"
              : "bg-gray-400"
          )}
        />
        {status}
      </span>
      {isDemo && (
        <span
          data-testid="demo-mode-badge"
          className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-400 tracking-wider shadow-sm"
        >
          [DEMO-MODE]
        </span>
      )}
    </div>
  );
}
