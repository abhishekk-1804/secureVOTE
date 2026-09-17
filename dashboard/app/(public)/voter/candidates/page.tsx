"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { User, Users } from "lucide-react";
import { useActiveElection } from "@/lib/hooks/useActiveElection";
import { api } from "@/lib/api-client";
import { formatApiError } from "@/lib/format-error";

export default function CandidatesPage() {
  const { election, loading: electionLoading, error: electionError } = useActiveElection();
  const [candidates, setCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!election) return;

    async function fetchCandidates() {
      setLoading(true);
      try {
        const response = await api.getTransparencyCandidates(election!.id);
        setCandidates(response);
      } catch (err) {
        setError(formatApiError(err));
      } finally {
        setLoading(false);
      }
    }

    fetchCandidates();
  }, [election]);

  if (electionLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="mb-8">
          <Skeleton className="h-10 w-64 mb-2" />
          <Skeleton className="h-5 w-96" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (electionError) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <ErrorState title="Error Loading Election" message={electionError} />
      </div>
    );
  }

  if (!election) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <EmptyState
          icon={Users}
          title="No Active Elections"
          description="There are currently no active elections to view candidates for."
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Candidates</h1>
        <p className="text-slate-600">
          Viewing candidates for: <span className="font-semibold text-slate-800">{election.title}</span>
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : error ? (
        <ErrorState title="Error Loading Candidates" message={error} />
      ) : candidates.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No Candidates Found"
          description="No candidates have been registered for this election yet."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {candidates.map((candidate) => (
            <Card key={candidate.id} className="overflow-hidden flex flex-col">
              <div className="bg-slate-100 p-6 flex justify-center items-center border-b border-slate-200">
                <div className="h-20 w-20 bg-white rounded-full flex items-center justify-center shadow-sm border border-slate-200">
                  <User className="h-10 w-10 text-slate-400" />
                </div>
              </div>
              <CardContent className="pt-4 flex-1">
                <h3 className="text-xl font-bold text-center mb-1 text-slate-900">{candidate.name}</h3>
                <p className="text-sm font-medium text-center text-indigo-600 mb-4">{candidate.party}</p>

                <div className="space-y-2 mt-auto">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Position:</span>
                    <span className="font-medium text-slate-800">{candidate.position}</span>
                  </div>
                  {candidate.symbol && (
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Symbol:</span>
                      <span className="font-medium text-slate-800">{candidate.symbol}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
