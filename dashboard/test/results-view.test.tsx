import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import ResultsPage from "@/app/results/page";
import { api } from "@/lib/api-client";
import { VerificationResponse } from "@/lib/types";

// Mock AuthContext
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "1", username: "auditor", role: "AUDITOR", is_active: true, created_at: "" },
    token: "mock-token",
    role: "AUDITOR",
    logout: vi.fn(),
  }),
}));

// Mock API client
vi.mock("@/lib/api-client", () => ({
  api: {
    getElections: vi.fn(),
    getResults: vi.fn(),
    runVerification: vi.fn(),
  },
}));

const mockVerificationData: VerificationResponse = {
  election_id: "EV-2026-001",
  config_hash_valid: true,
  audit_chain_intact: true,
  reconciliation_passed: true,
  tally_independently_verified: true,
  overall_status: "PASSED",
  details: ["Reconciliation passed. 1000 ballots across 4 candidates."],
  manifest: {
    id: "man-001",
    election_id: "EV-2026-001",
    total_ballots: 1000,
    candidate_totals: JSON.stringify({ C001: 300, C002: 250, C003: 250, C004: 200 }),
    device_totals: JSON.stringify({ "EVM-001": 250, "EVM-002": 250, "EVM-003": 250, "EVM-004": 250 }),
    reconciliation_status: "PASSED",
    audit_chain_status: "INTACT",
    configuration_hash: "34d70b0c609559c403328e1215b3e6c0c5980e07cb185b3db5c088c445a49f87",
    manifest_hash: "abcd1234ef567890abcd1234ef567890abcd1234ef567890abcd1234ef567890",
    digital_signature: null,
    generated_at: "2026-09-16T12:00:00Z",
    verified_at: "2026-09-16T12:00:00Z",
    verified_by: "auditor",
    candidate_results: [
      {
        candidate_id: "C001",
        candidate_name: "Alice Vance",
        party: "Forward Alliance",
        symbol: "A",
        vote_count: 300,
        percentage: 30.0,
      },
      {
        candidate_id: "C002",
        candidate_name: "Bob Jenkins",
        party: "Civic Liberty",
        symbol: "B",
        vote_count: 250,
        percentage: 25.0,
      },
      {
        candidate_id: "C003",
        candidate_name: "Carol Danvers",
        party: "Reform Union",
        symbol: "C",
        vote_count: 250,
        percentage: 25.0,
      },
      {
        candidate_id: "C004",
        candidate_name: "David Miller",
        party: "Independent Coalition",
        symbol: "D",
        vote_count: 200,
        percentage: 20.0,
      },
    ],
    device_results: [
      { device_id: "EVM-001", device_name: "Precinct 1", ballot_count: 250 },
      { device_id: "EVM-002", device_name: "Precinct 2", ballot_count: 250 },
      { device_id: "EVM-003", device_name: "Precinct 3", ballot_count: 250 },
      { device_id: "EVM-004", device_name: "Precinct 4", ballot_count: 250 },
    ],
    reconciliation: {
      total_ballots: 1000,
      sum_candidate_totals: 1000,
      sum_device_totals: 1000,
      is_exact_match: true,
      status: "PASSED",
    },
  },
};

describe("ResultsPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getElections as any).mockResolvedValue([
      { id: "EV-2026-001", title: "General Election 2026", state: "CLOSED" },
    ]);
    (api.getResults as any).mockResolvedValue(mockVerificationData);
  });

  it("renders overall independent verification status as PASSED", async () => {
    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Independent Verification: PASSED/i)).toBeInTheDocument();
    });

    expect(screen.getByText("FROZEN & VALID")).toBeInTheDocument();
    expect(screen.getByText("CHAIN INTACT")).toBeInTheDocument();
    expect(screen.getByText("EXACT ZERO-DRIFT")).toBeInTheDocument();
    expect(screen.getByText("RECOUNT MATCHES")).toBeInTheDocument();
  });

  it("renders candidate tallies and vote percentages correctly", async () => {
    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Alice Vance")).toBeInTheDocument();
    });

    expect(screen.getByText("300 votes")).toBeInTheDocument();
    expect(screen.getByText("(30.00%)")).toBeInTheDocument();
    expect(screen.getByText("Bob Jenkins")).toBeInTheDocument();
    expect(screen.getByText("David Miller")).toBeInTheDocument();
  });

  it("displays exact zero-drift reconciliation values", async () => {
    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Reconciliation Breakdown/i)).toBeInTheDocument();
    });

    // Check mathematical identity display
    expect(screen.getByText("0 (Exact match)")).toBeInTheDocument();
  });

  it("toggles the signed result manifest JSON document", async () => {
    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("View Signed Manifest")).toBeInTheDocument();
    });

    const button = screen.getByText("View Signed Manifest");
    fireEvent.click(button);

    expect(screen.getByText(/Signed Result Manifest Document/i)).toBeInTheDocument();
    expect(screen.getAllByText(/abcd1234ef567890/i).length).toBeGreaterThan(0);
  });
});
