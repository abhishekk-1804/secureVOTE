"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  BarChart3,
  ScrollText,
  ShieldAlert,
  Cpu,
  Info,
} from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  {
    label: "Command Center",
    href: "/command",
    icon: LayoutDashboard,
  },
  {
    label: "Results & Verification",
    href: "/results",
    icon: BarChart3,
  },
  {
    label: "Audit Explorer",
    href: "/audit",
    icon: ScrollText,
  },
  {
    label: "Security Center",
    href: "/security",
    icon: ShieldAlert,
  },
  {
    label: "Device Management",
    href: "/devices",
    icon: Cpu,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 text-slate-300 min-h-[calc(100vh-4rem)] flex flex-col justify-between p-4 shrink-0">
      <nav className="space-y-1.5" aria-label="Main Navigation">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              )}
            >
              <Icon
                className={clsx(
                  "w-4 h-4",
                  isActive ? "text-blue-400" : "text-slate-500"
                )}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="pt-4 border-t border-slate-800">
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3 text-xs text-slate-400">
          <div className="flex items-center gap-1.5 font-semibold text-slate-300 mb-1">
            <Info className="w-3.5 h-3.5 text-blue-400" />
            Trust Boundary Notice
          </div>
          <p className="leading-relaxed text-[11px]">
            Dashboard is presentation-only. All verification properties are
            recalculated from raw records by the independent verifier.
          </p>
        </div>
      </div>
    </aside>
  );
}
