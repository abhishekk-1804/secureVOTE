"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { ShieldCheck, LogOut, User as UserIcon } from "lucide-react";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ElectionSelector } from "@/components/election/ElectionSelector";

export function Navbar() {
  const { user, role, logout } = useAuth();

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="bg-emerald-600 p-2 rounded-lg text-white shadow-md group-hover:bg-emerald-500 transition">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-white flex items-center gap-2">
                SecureVOTE
                <span className="text-[10px] uppercase font-semibold tracking-wider bg-emerald-950 text-emerald-300 border border-emerald-700/60 px-1.5 py-0.5 rounded">
                  v3.3 Research
                </span>
              </span>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                India Election Security &amp; Cryptographic Verification Platform
              </p>
            </div>
          </Link>
        </div>

        {/* Center Navigation Links for Research Platform */}
        <nav className="hidden lg:flex items-center gap-1 text-xs font-medium text-slate-300">
          <Link
            href="/"
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-slate-800 transition-colors"
          >
            Command Center
          </Link>
          <Link
            href="/map"
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-slate-800 transition-colors"
          >
            Electoral Map
          </Link>
          <Link
            href="/verify"
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-slate-800 transition-colors"
          >
            Verifier
          </Link>
          <Link
            href="/research"
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-slate-800 transition-colors"
          >
            Research
          </Link>
          <Link
            href="/evm"
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-slate-800 transition-colors"
          >
            EVM Terminal
          </Link>
        </nav>

        <div className="flex items-center gap-4">
          <ElectionSelector />
          {user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-full py-1 px-3">
                <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-xs font-medium text-slate-200">
                  {user.username}
                </span>
                {role && <StatusBadge status={role} />}
              </div>
              <button
                onClick={logout}
                className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition"
                title="Log out"
                aria-label="Log out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg transition"
            >
              Log in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
