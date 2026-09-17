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
        const elections = await api.getElections();
        if (elections.length > 0) {
          // Prefer OPEN election, then most recent
          const open = elections.find(e => e.state === 'OPEN');
          setElection(open || elections[0]);
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
