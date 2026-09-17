"use client";
import React, { createContext, useContext, useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { ElectionResponse } from "@/lib/types";
import { useAuth } from "@/context/AuthContext";

interface ElectionContextType {
  elections: ElectionResponse[];
  selectedElection: ElectionResponse | null;
  selectElection: (id: string) => void;
  refreshElections: () => Promise<void>;
  loading: boolean;
}

const ElectionContext = createContext<ElectionContextType | undefined>(undefined);

export function ElectionProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const [elections, setElections] = useState<ElectionResponse[]>([]);
  const [selectedElection, setSelectedElection] = useState<ElectionResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshElections = async () => {
    try {
      const all = await api.getElections(token);
      setElections(all);
      if (all.length > 0 && !selectedElection) {
        const detailed = await api.getElection(all[0].id, token);
        setSelectedElection(detailed);
      } else if (selectedElection) {
        const refreshed = await api.getElection(selectedElection.id, token);
        setSelectedElection(refreshed);
      }
    } catch {
      // handle error
    } finally {
      setLoading(false);
    }
  };

  const selectElection = async (id: string) => {
    try {
      const detailed = await api.getElection(id, token);
      setSelectedElection(detailed);
    } catch {
      // handle error
    }
  };

  useEffect(() => {
    if (token) refreshElections();
  }, [token]);

  return (
    <ElectionContext.Provider value={{ elections, selectedElection, selectElection, refreshElections, loading }}>
      {children}
    </ElectionContext.Provider>
  );
}

export function useElection() {
  const ctx = useContext(ElectionContext);
  if (!ctx) throw new Error("useElection must be used within ElectionProvider");
  return ctx;
}
