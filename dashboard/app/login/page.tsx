"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Shield, KeyRound, User, Lock, AlertCircle } from "lucide-react";
import { AlertBanner } from "@/components/common/AlertBanner";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: any) {
      setError(err.message || "Failed to log in. Please verify credentials.");
    } finally {
      setLoading(false);
    }
  };

  const setDemoCreds = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
  };

  return (
    <div className="flex items-center justify-center min-h-[75vh] px-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
        <div className="text-center mb-6">
          <div className="inline-flex p-3 bg-blue-600/20 border border-blue-500/30 rounded-xl text-blue-400 mb-3">
            <Shield className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            SecureVOTE Console
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Authenticate to manage election lifecycle and audit verifications
          </p>
        </div>

        {error && (
          <AlertBanner
            type="error"
            title="Authentication Failed"
            message={error}
            className="mb-5"
          />
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Username
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                placeholder="Enter username"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm rounded-lg transition shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <KeyRound className="w-4 h-4" />
                Sign In
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-slate-800">
          <div className="mb-3 p-2 bg-rose-950/30 border border-rose-500/30 rounded text-[11px] text-rose-300 font-mono text-center">
            ⚠ LOCAL DEMO CREDENTIALS — Synthetic environment only. Never use in production.
          </div>
          <p className="text-xs font-semibold text-slate-400 mb-2">
            Pre-seeded Accounts (Local Demonstration Only):
          </p>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <button
              type="button"
              onClick={() => setDemoCreds("admin", "adminpass")}
              className="p-2 bg-slate-800 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition text-slate-300"
            >
              <div className="font-bold text-indigo-400">ADMIN</div>
              <div className="text-[10px] text-slate-500">admin / adminpass</div>
            </button>
            <button
              type="button"
              onClick={() => setDemoCreds("auditor", "auditorpass")}
              className="p-2 bg-slate-800 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition text-slate-300"
            >
              <div className="font-bold text-teal-400">AUDITOR</div>
              <div className="text-[10px] text-slate-500">auditor / auditorpass</div>
            </button>
            <button
              type="button"
              onClick={() => setDemoCreds("observer", "observerpass")}
              className="p-2 bg-slate-800 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition text-slate-300"
            >
              <div className="font-bold text-slate-400">OBSERVER</div>
              <div className="text-[10px] text-slate-500">observer / observerpass</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
