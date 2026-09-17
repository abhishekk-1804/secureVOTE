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
          <Link href="/command" className="flex items-center gap-2.5 group">
            <div className="bg-blue-600 p-2 rounded-lg text-white shadow-md group-hover:bg-blue-500 transition">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-white flex items-center gap-2">
                SecureVOTE
                <span className="text-[10px] uppercase font-semibold tracking-wider bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded">
                  Prototype
                </span>
              </span>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Educational Embedded Voting & Audit System
              </p>
            </div>
          </Link>
        </div>

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
              className="text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg transition"
            >
              Log in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
