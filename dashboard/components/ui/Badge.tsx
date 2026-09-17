import React from "react";
import clsx from "clsx";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "success" | "warning" | "danger" | "info" | "neutral";
  className?: string;
}

export function Badge({ children, variant = "neutral", className }: BadgeProps) {
  const variants = {
    success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
    warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
    danger: "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400",
    info: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
    neutral: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300",
  };

  return (
    <span className={clsx("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium", variants[variant], className)}>
      {children}
    </span>
  );
}
