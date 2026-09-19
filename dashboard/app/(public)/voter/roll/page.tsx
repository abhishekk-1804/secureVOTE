"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { VoterResponse } from "@/lib/types";
import { useActiveElection } from "@/lib/hooks/useActiveElection";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  Users,
  Search,
  ArrowLeft,
  Info,
  CheckCircle2,
  XCircle,
  FileText,
} from "lucide-react";

const DEMO_VOTERS: VoterResponse[] = [
  {
    id: "1",
    election_id: "EV-2026-001",
    voter_id_number: "VTR-00101",
    name: "Aarav Sharma",
    date_of_birth: "1994-05-12",
    constituency: "Bengaluru Central (Karnataka)",
    polling_station_id: "PS-001",
    eligibility_status: "ELIGIBLE",
    registration_status: "VERIFIED",
    has_voted: true,
    registered_at: new Date().toISOString(),
  },
  {
    id: "2",
    election_id: "EV-2026-001",
    voter_id_number: "VTR-00102",
    name: "Meera Patel",
    date_of_birth: "1988-11-23",
    constituency: "Mumbai South (Maharashtra)",
    polling_station_id: "PS-002",
    eligibility_status: "ELIGIBLE",
    registration_status: "VERIFIED",
    has_voted: false,
    registered_at: new Date().toISOString(),
  },
  {
    id: "3",
    election_id: "EV-2026-001",
    voter_id_number: "VTR-00103",
    name: "Rohan Iyer",
    date_of_birth: "2001-02-17",
    constituency: "New Delhi (NCT)",
    polling_station_id: "PS-003",
    eligibility_status: "ELIGIBLE",
    registration_status: "VERIFIED",
    has_voted: false,
    registered_at: new Date().toISOString(),
  },
  {
    id: "4",
    election_id: "EV-2026-001",
    voter_id_number: "VTR-00104",
    name: "Pooja Verma",
    date_of_birth: "1997-09-30",
    constituency: "Varanasi (Uttar Pradesh)",
    polling_station_id: "PS-001",
    eligibility_status: "ELIGIBLE",
    registration_status: "VERIFIED",
    has_voted: true,
    registered_at: new Date().toISOString(),
  },
  {
    id: "5",
    election_id: "EV-2026-001",
    voter_id_number: "VTR-00105",
    name: "Debashis Banerjee",
    date_of_birth: "1985-07-14",
    constituency: "Kolkata Dakshin (West Bengal)",
    polling_station_id: "PS-004",
    eligibility_status: "ELIGIBLE",
    registration_status: "VERIFIED",
    has_voted: false,
    registered_at: new Date().toISOString(),
  },
];

export default function ElectoralRollPage() {
  const { election, loading: electionLoading } = useActiveElection();
  const [voters, setVoters] = useState<VoterResponse[]>(DEMO_VOTERS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedConstituency, setSelectedConstituency] = useState("ALL");
  const [loading, setLoading] = useState(false);
  const [lookupNotice, setLookupNotice] = useState<string | null>(null);

  // The public electoral roll browser initializes with the simulated Indian electors dataset.
  // Individual real-time verification lookups are performed on-demand via public api.lookupVoter.

  const handleLookup = async () => {
    const q = searchQuery.trim();
    if (!q) {
      setLookupNotice(null);
      return;
    }
    setLoading(true);
    setLookupNotice(null);
    try {
      const elId = election?.id || "EV-2026-001";
      const result = await api.lookupVoter(elId, q);
      if (result) {
        setVoters((prev) => {
          const exists = prev.some((v) => v.voter_id_number === result.voter_id_number);
          return exists ? prev : [result, ...prev];
        });
        setLookupNotice(`Live record found for ${result.name} (${result.voter_id_number})`);
      }
    } catch {
      setLookupNotice(`No backend database record found for "${q}". Filtered local demonstrator roll.`);
    } finally {
      setLoading(false);
    }
  };

  const filteredVoters = voters.filter((v) => {
    const matchesSearch =
      v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      v.voter_id_number.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesConst =
      selectedConstituency === "ALL" || v.constituency === selectedConstituency;
    return matchesSearch && matchesConst;
  });

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div>
        <Link href="/voter" className="inline-flex items-center text-xs text-slate-500 hover:text-slate-800">
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Voter Portal
        </Link>
      </div>

      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <FileText className="w-6 h-6 text-blue-600" />
          Simulated Electoral Roll
        </h1>
        <p className="text-xs text-slate-500">
          Search the constituency electoral register to verify registration status and polling assignments.
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-900 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold">Simulated Demonstration Data:</span> All names, IDs, and voter statuses shown below are synthetically generated for educational research. Never enter or search real identity credentials.
        </div>
      </div>

      <Card>
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="w-full sm:flex-1 flex gap-2">
            <Input
              placeholder="Search by Name or Voter ID (e.g., VTR-00101)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLookup()}
            />
            <Button
              variant="secondary"
              onClick={handleLookup}
              disabled={loading}
              className="shrink-0"
            >
              <Search className="w-4 h-4 mr-1.5" />
              {loading ? "Searching..." : "Lookup"}
            </Button>
          </div>
          <div className="w-full sm:w-64">
            <Select
              value={selectedConstituency}
              onChange={(e) => setSelectedConstituency(e.target.value)}
              options={[
                { value: "ALL", label: "All Constituencies" },
                { value: "Bengaluru Central (Karnataka)", label: "Bengaluru Central (Karnataka)" },
                { value: "Mumbai South (Maharashtra)", label: "Mumbai South (Maharashtra)" },
                { value: "New Delhi (NCT)", label: "New Delhi (NCT)" },
                { value: "Varanasi (Uttar Pradesh)", label: "Varanasi (Uttar Pradesh)" },
                { value: "Kolkata Dakshin (West Bengal)", label: "Kolkata Dakshin (West Bengal)" },
              ]}
            />
          </div>
        </div>
      </Card>

      {lookupNotice && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 flex items-center justify-between">
          <span>{lookupNotice}</span>
          <button
            type="button"
            onClick={() => setLookupNotice(null)}
            className="text-blue-600 hover:text-blue-900 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      <div className="space-y-3">
        <div className="flex justify-between items-center text-xs text-slate-500 px-1">
          <span>Showing {filteredVoters.length} Registered Voter(s)</span>
          <span>Constituency: {selectedConstituency}</span>
        </div>

        <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl bg-white overflow-hidden shadow-sm">
          {filteredVoters.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No matching simulated voter records found.
            </div>
          ) : (
            filteredVoters.map((v) => (
              <div key={v.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-blue-600">
                      {v.voter_id_number}
                    </span>
                    <Badge variant={v.registration_status === "VERIFIED" ? "success" : "neutral"}>
                      {v.registration_status}
                    </Badge>
                  </div>
                  <p className="text-sm font-semibold text-slate-900">{v.name}</p>
                  <p className="text-xs text-slate-500">
                    Constituency: {v.constituency} • Polling Station: {v.polling_station_id || "Unassigned"}
                  </p>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  {v.has_voted ? (
                    <span className="flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full font-medium border border-emerald-200">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Vote Recorded
                    </span>
                  ) : (
                    <span className="text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
                      Not Yet Voted
                    </span>
                  )}
                  <Link href={`/voter/profile?voterId=${v.voter_id_number}`}>
                    <Button variant="outline" size="sm">
                      View Profile
                    </Button>
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
