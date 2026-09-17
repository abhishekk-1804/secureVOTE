import React from "react";
import clsx from "clsx";

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { label: string; value: string | number }[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            {label}
          </label>
        )}
        <select
          ref={ref}
          className={clsx(
            "flex w-full rounded-md border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-900",
            error
              ? "border-rose-500 focus:ring-rose-500"
              : "border-slate-300 focus:ring-blue-500 dark:border-slate-700",
            className
          )}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <p className="mt-1 text-sm text-rose-500">{error}</p>}
      </div>
    );
  }
);
Select.displayName = "Select";
