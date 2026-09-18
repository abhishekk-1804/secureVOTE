"use client";

import React, { useState } from "react";

interface Props {
  onInitSession: (creds?: { u: string, p: string }) => void;
  onConfirm: () => void;
  onCancel: () => void;
  canInit: boolean;
  canConfirm: boolean;
  canCancel: boolean;
  isAuthed: boolean;
}

export default function EvmControlPanel({ onInitSession, onConfirm, onCancel, canInit, canConfirm, canCancel, isAuthed }: Props) {
  const [showLogin, setShowLogin] = useState(false);
  const [u, setU] = useState("");
  const [p, setP] = useState("");

  const handleInit = () => {
    if (isAuthed) {
      onInitSession();
    } else {
      setShowLogin(true);
    }
  };

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowLogin(false);
    onInitSession({ u, p });
  };

  return (
    <div className="bg-slate-900 border-2 border-slate-700 rounded-lg p-6 shadow-inner flex flex-col gap-4">
      {showLogin ? (
        <form onSubmit={handleLoginSubmit} className="flex flex-col gap-3">
          <div className="text-xs font-mono text-amber-500 mb-1">OFFICER LOGIN REQUIRED</div>
          <input
            type="text" placeholder="Username"
            className="bg-slate-950 border border-slate-700 rounded p-2 text-sm text-slate-100"
            value={u} onChange={e => setU(e.target.value)}
          />
          <input
            type="password" placeholder="Password"
            className="bg-slate-950 border border-slate-700 rounded p-2 text-sm text-slate-100"
            value={p} onChange={e => setP(e.target.value)}
          />
          <button
            type="button"
            onClick={() => { setU("officer"); setP("OfficerSecurePassword123!"); }}
            className="text-xs text-amber-400 hover:text-amber-300 text-left underline underline-offset-2"
          >
            Use Local Demo Credentials (officer / demo-only)
          </button>
          <div className="text-[10px] text-rose-400 bg-rose-950/30 border border-rose-500/30 rounded p-1.5 font-mono">
            ⚠ LOCAL DEMO CREDENTIALS — Synthetic environment only. Never use in production.
          </div>
          <div className="flex gap-2">
            <button type="submit" className="flex-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold py-2 rounded text-sm transition-colors">LOGIN & INIT</button>
            <button type="button" onClick={() => setShowLogin(false)} className="px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-sm">Cancel</button>
          </div>
        </form>
      ) : (
        <button
          onClick={handleInit}
          disabled={!canInit}
          className={`py-4 px-4 font-bold rounded-lg shadow-lg border-b-4 active:border-b-0 active:translate-y-1 transition-all ${
            canInit ? "bg-indigo-600 border-indigo-800 text-white hover:bg-indigo-500" : "bg-slate-800 border-slate-900 text-slate-500 cursor-not-allowed"
          }`}
        >
          INITIALIZE TEST SESSION
        </button>
      )}

      <div className="grid grid-cols-2 gap-3 mt-4">
        <button
          onClick={onCancel}
          disabled={!canCancel}
          className={`py-4 font-bold rounded-lg shadow-lg border-b-4 active:border-b-0 active:translate-y-1 transition-all ${
            canCancel ? "bg-red-600 border-red-800 text-white hover:bg-red-500" : "bg-slate-800 border-slate-900 text-slate-500 cursor-not-allowed"
          }`}
        >
          CANCEL
        </button>

        <button
          onClick={onConfirm}
          disabled={!canConfirm}
          className={`py-4 font-bold rounded-lg shadow-lg border-b-4 active:border-b-0 active:translate-y-1 transition-all ${
            canConfirm ? "bg-emerald-600 border-emerald-800 text-white hover:bg-emerald-500" : "bg-slate-800 border-slate-900 text-slate-500 cursor-not-allowed"
          }`}
        >
          CONFIRM
        </button>
      </div>
    </div>
  );
}
