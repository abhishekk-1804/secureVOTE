"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { Search, FileText, CheckCircle, Clock } from "lucide-react";
import { api } from "@/lib/api-client";
import { formatApiError } from "@/lib/format-error";

export default function VotingStatusPage() {
  const [voterId, setVoterId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voterData, setVoterData] = useState<any | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!voterId.trim()) return;

    setLoading(true);
    setError(null);
    setVoterData(null);

    try {
      // Assuming api.lookupVoter exists
      const response = await api.lookupVoter("mock-election", voterId);
      setVoterData(response);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container max-w-3xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Voting Status</h1>
        <p className="text-slate-600">Track your registration and check your voting record.</p>
      </div>

      <Card className="mb-8">
        <CardContent className="pt-6">
          <form onSubmit={handleSearch} className="flex gap-4">
            <div className="flex-1">
              <Input
                placeholder="Enter Voter ID (e.g., VTR-12345)"
                value={voterId}
                onChange={(e) => setVoterId(e.target.value)}
                disabled={loading}
                className="text-lg py-6"
              />
            </div>
            <Button type="submit" disabled={loading || !voterId.trim()} loading={loading} className="py-6 px-8">
              <Search className="h-5 w-5 mr-2" />
              Lookup
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <ErrorState
          title="Lookup Failed"
          message={error}
          onRetry={() => setError(null)}
        />
      )}

      {voterData && (
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <FileText className="h-5 w-5 mr-2 text-indigo-500" />
                Voter Profile
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-slate-500">Name</p>
                <p className="font-medium text-slate-900">{voterData.name || 'Unknown'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Constituency</p>
                <p className="font-medium text-slate-900">{voterData.constituency || 'Unknown'}</p>
              </div>
              <div className="flex gap-4">
                <div>
                  <p className="text-sm text-slate-500 mb-1">Registration</p>
                  <Badge variant={voterData.registrationStatus === 'ACTIVE' ? 'success' : 'neutral'}>
                    {voterData.registrationStatus || 'PENDING'}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Eligibility</p>
                  <Badge variant={voterData.eligibility === 'ELIGIBLE' ? 'success' : 'warning'}>
                    {voterData.eligibility || 'UNKNOWN'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className={voterData.hasVoted ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200'}>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <CheckCircle className={`h-5 w-5 mr-2 ${voterData.hasVoted ? 'text-emerald-500' : 'text-slate-400'}`} />
                Voting Record
              </CardTitle>
            </CardHeader>
            <CardContent>
              {voterData.hasVoted ? (
                <div className="text-center py-4">
                  <div className="inline-flex items-center justify-center p-3 bg-emerald-100 rounded-full mb-3">
                    <CheckCircle className="h-8 w-8 text-emerald-600" />
                  </div>
                  <h3 className="text-xl font-bold text-emerald-800 mb-1">VOTE RECORDED</h3>
                  <p className="text-emerald-600 text-sm mb-4">Your vote has been securely logged.</p>

                  <div className="bg-white p-3 rounded border border-emerald-100 text-left">
                    <p className="text-xs text-slate-500">Transaction Reference (Tamper-evident log)</p>
                    <p className="font-mono text-xs text-slate-700 truncate">{voterData.voteReference || 'N/A'}</p>
                    <p className="text-xs text-slate-400 mt-2 italic">* Selection details remain strictly private.</p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-6">
                  <Clock className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                  <h3 className="text-lg font-medium text-slate-700">NO VOTE RECORDED YET</h3>
                  <p className="text-slate-500 text-sm mt-1">
                    You have not cast a vote in the active election.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
