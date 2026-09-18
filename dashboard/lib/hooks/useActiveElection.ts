"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { ElectionResponse } from "@/lib/types";

export function useActiveElection() {
  const [election, setElection] = useState<ElectionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        let elections: any[] = [];
        try {
          elections = await api.getElections();
        } catch {
          // Fall back to unauthenticated public transparency
        }

        if (!elections || elections.length === 0) {
          try {
            const publicElections = await api.getTransparencyElections();
            elections = publicElections.map(e => ({
              id: e.election_id,
              name: e.election_name,
              title: e.election_name,
              state: e.state,
              total_ballots: e.total_ballots,
              device_count: e.device_count,
            }));
          } catch {}
        }

        if (elections.length > 0) {
          // Prefer OPEN election, then most recent
          const open = elections.find(e => e.state === 'OPEN');
          const chosen = open || elections[0];
          setElection({
            ...chosen,
            name: chosen.name || chosen.title || chosen.id,
            title: chosen.name || chosen.title || chosen.id,
          });
        }
      } catch (err: any) {
        setError(err.message || 'Unable to load election data');
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  return { election, loading, error };
}
