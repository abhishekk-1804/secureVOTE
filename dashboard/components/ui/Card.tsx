import React from "react";
import clsx from "clsx";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
}

export function Card({ children, className, padding = "md" }: CardProps) {
  const paddings = { none: "", sm: "p-4", md: "p-6", lg: "p-8" };
  return (
    <div className={clsx("bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm", paddings[padding], className)}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx("pb-4 border-b border-slate-200 dark:border-slate-800", className)}>{children}</div>;
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h3 className={clsx("text-lg font-bold text-slate-900 dark:text-white", className)}>{children}</h3>;
}

export function CardDescription({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={clsx("text-sm text-slate-500 dark:text-slate-400 mt-1", className)}>{children}</p>;
}

export function CardContent({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx("pt-4", className)}>{children}</div>;
}

export function CardFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx("pt-4 border-t border-slate-200 dark:border-slate-800", className)}>{children}</div>;
}
