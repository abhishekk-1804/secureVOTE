import React from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "./Button";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ title = "Something went wrong", message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-rose-50 dark:bg-rose-950/20 rounded-lg border border-rose-200 dark:border-rose-900">
      <AlertTriangle className="w-12 h-12 text-rose-500 mb-4" />
      <h3 className="text-lg font-medium text-rose-900 dark:text-rose-100 mb-2">{title}</h3>
      <p className="text-sm text-rose-600 dark:text-rose-400 max-w-md mb-6">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="bg-white dark:bg-transparent">
          Try Again
        </Button>
      )}
    </div>
  );
}
