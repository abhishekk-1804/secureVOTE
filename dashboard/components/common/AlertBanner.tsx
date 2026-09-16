import React from "react";
import { AlertTriangle, CheckCircle, Info, XCircle, X } from "lucide-react";
import clsx from "clsx";

interface AlertBannerProps {
  type?: "error" | "warning" | "success" | "info";
  title?: string;
  message: React.ReactNode;
  onDismiss?: () => void;
  className?: string;
}

export function AlertBanner({
  type = "info",
  title,
  message,
  onDismiss,
  className,
}: AlertBannerProps) {
  const styles = {
    error: {
      bg: "bg-rose-50 border-rose-200 text-rose-800",
      icon: <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />,
    },
    warning: {
      bg: "bg-amber-50 border-amber-200 text-amber-900",
      icon: <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />,
    },
    success: {
      bg: "bg-emerald-50 border-emerald-200 text-emerald-800",
      icon: <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />,
    },
    info: {
      bg: "bg-blue-50 border-blue-200 text-blue-800",
      icon: <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />,
    },
  }[type];

  return (
    <div
      role="alert"
      className={clsx(
        "border rounded-lg p-3.5 flex items-start justify-between gap-3 text-sm transition-all",
        styles.bg,
        className
      )}
    >
      <div className="flex items-start gap-3">
        {styles.icon}
        <div>
          {title && <h4 className="font-semibold mb-0.5">{title}</h4>}
          <div className="leading-relaxed">{message}</div>
        </div>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-gray-400 hover:text-gray-600 p-1 rounded-md transition"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
