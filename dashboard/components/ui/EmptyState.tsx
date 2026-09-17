import React from "react";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-dashed border-slate-200 dark:border-slate-800">
      <Icon className="w-12 h-12 text-slate-400 mb-4" />
      <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-2">{title}</h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mb-6">{description}</p>
      {action}
    </div>
  );
}
