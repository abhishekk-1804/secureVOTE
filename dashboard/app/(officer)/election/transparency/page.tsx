"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { Eye, ExternalLink, Globe } from "lucide-react";
import Link from "next/link";

export default function TransparencyPreviewPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      if (!selectedElection) return;
      setLoading(true);
      try {
        const overview = await api.getTransparencyOverview(selectedElection.id);
        setData(overview);
      } catch (err: any) {
        setError(formatApiError(err));
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [selectedElection]);

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view transparency preview.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Eye className="w-6 h-6 text-blue-500" />
          Transparency Preview
        </h1>
        <Link
          href={`/transparency/${selectedElection.id}`}
          target="_blank"
          className="bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded-md font-medium flex items-center gap-2 text-sm"
        >
          <ExternalLink className="w-4 h-4" /> View Public Portal
        </Link>
      </div>

      <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-4 text-sm text-slate-300">
        This page shows a preview of the data available to the public on the transparency portal.
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden relative">
        <div className="absolute top-0 right-0 bg-blue-600 text-white text-[10px] font-bold px-3 py-1 uppercase tracking-wider rounded-bl-lg">
          Public View Preview
        </div>

        <div className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <Globe className="w-8 h-8 text-slate-400" />
            <div>
              <h2 className="text-xl font-bold">{data?.title || selectedElection.title}</h2>
              <div className="text-sm text-slate-400">Status: {data?.state || selectedElection.state}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
              <div className="text-sm text-slate-500 mb-1">Total Ballots</div>
              <div className="text-2xl font-bold font-mono text-emerald-400">{data?.total_ballots ?? selectedElection.ballot_count}</div>
            </div>
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
              <div className="text-sm text-slate-500 mb-1">Config Hash</div>
              <div className="text-sm font-mono text-slate-300 break-all">{selectedElection.configuration_hash?.substring(0,16) || selectedElection.configuration_hash?.substring(0,16)}...</div>
            </div>
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
              <div className="text-sm text-slate-500 mb-1">Result Published</div>
              <div className="text-lg font-bold text-slate-200">{(data?.state || selectedElection.state) === 'PUBLISHED' ? 'Yes' : 'No'}</div>
            </div>
          </div>

          <div className="text-sm text-slate-400 italic text-center p-4 bg-slate-950 rounded-lg">
            Citizens can use the public portal to verify their individual vote inclusion and audit the mathematical proofs without viewing individual choices.
          </div>
        </div>
      </div>
    </div>
  );
}
