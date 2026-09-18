"use client";

import React from "react";
import clsx from "clsx";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  as?: "button" | "span";
  children: React.ReactNode;
}

export function Button({ variant = "primary", size = "md", loading, as = "button", children, className, disabled, type = "button", ...props }: ButtonProps) {
  const base = "inline-flex items-center justify-center gap-2 font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
    secondary: "bg-slate-700 text-white hover:bg-slate-600 focus:ring-slate-500",
    outline: "border border-slate-300 text-slate-700 hover:bg-slate-50 focus:ring-blue-500 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800",
    ghost: "text-slate-600 hover:bg-slate-100 focus:ring-slate-500 dark:text-slate-400 dark:hover:bg-slate-800",
    danger: "bg-rose-600 text-white hover:bg-rose-700 focus:ring-rose-500",
  };
  const sizes = {
    sm: "text-xs px-3 py-1.5",
    md: "text-sm px-4 py-2",
    lg: "text-base px-6 py-3",
  };

  const combinedClass = clsx(base, variants[variant], sizes[size], className);

  if (as === "span") {
    return (
      <span className={combinedClass}>
        {loading && <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />}
        {children}
      </span>
    );
  }

  return (
    <button
      type={type}
      className={combinedClass}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />}
      {children}
    </button>
  );
}
