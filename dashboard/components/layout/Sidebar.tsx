"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Settings,
  Users,
  MapPin,
  Cpu,
  Vote,
  Calculator,
  BarChart3,
  CheckCircle,
  ScrollText,
  ShieldAlert,
  Zap,
  MessageSquare,
  Play,
  Eye,
  Info,
} from "lucide-react";
import clsx from "clsx";

const NAV_SECTIONS = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", href: "/command", icon: LayoutDashboard },
    ],
  },
  {
    title: "Election Operations",
    items: [
      { label: "Election Setup", href: "/election/setup", icon: Settings },
      { label: "Candidates", href: "/election/candidates", icon: Users },
      { label: "Polling Stations", href: "/election/polling-stations", icon: MapPin },
      { label: "Devices", href: "/election/devices", icon: Cpu },
      { label: "Polling", href: "/election/polling", icon: Vote },
    ],
  },
  {
    title: "Results & Verification",
    items: [
      { label: "Counting Center", href: "/election/counting", icon: Calculator },
      { label: "Results", href: "/election/results", icon: BarChart3 },
      { label: "Verification", href: "/election/verification", icon: CheckCircle },
    ],
  },
  {
    title: "Integrity & Security",
    items: [
      { label: "Audit Explorer", href: "/election/audit", icon: ScrollText },
      { label: "Security Center", href: "/election/security", icon: ShieldAlert },
      { label: "Attack Demo", href: "/election/attacks", icon: Zap },
    ],
  },
  {
    title: "Administration",
    items: [
      { label: "Complaints", href: "/election/complaints", icon: MessageSquare },
      { label: "Simulation", href: "/election/simulation", icon: Play },
      { label: "Transparency", href: "/election/transparency", icon: Eye },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 text-slate-300 min-h-[calc(100vh-4rem)] flex flex-col justify-between p-4 shrink-0 overflow-y-auto">
      <nav className="space-y-6" aria-label="Main Navigation">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title}>
            <h3 className="px-3 mb-2 text-xs font-semibold tracking-wider text-slate-500 uppercase">
              {section.title}
            </h3>
            <div className="space-y-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                      isActive
                        ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
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
            </div>
          </div>
        ))}
      </nav>

      <div className="pt-6 mt-6 border-t border-slate-800">
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
