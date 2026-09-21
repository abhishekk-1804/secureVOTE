import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import CommandCenterPage from "@/app/(officer)/command/page";
import ElectionSetupPage from "@/app/(officer)/election/setup/page";
import { ElectionProvider, useElection } from "@/context/ElectionContext";

// Mock AuthContext
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "1", username: "admin", role: "ADMIN", is_active: true, created_at: "" },
    token: "mock-token",
    role: "ADMIN",
    logout: vi.fn(),
  }),
}));

// Mock API Client
const mockGetElection = vi.fn();
const mockGetElections = vi.fn();
const mockUpdateElectionState = vi.fn();

vi.mock("@/lib/api-client", () => ({
  api: {
    getElections: (...args: any[]) => mockGetElections(...args),
    getElection: (...args: any[]) => mockGetElection(...args),
    updateElectionState: (...args: any[]) => mockUpdateElectionState(...args),
  },
}));

describe("Frontend Lifecycle Synchronization & Terminal State", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("displays terminal PUBLISHED state banner and hides transition buttons on command page", async () => {
    const publishedElection = {
      id: "EV-2026-001",
      title: "General Election 2026",
      name: "General Election 2026",
      state: "PUBLISHED",
      configuration_hash: "abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234",
      device_count: 3,
      ballot_count: 100,
      created_at: "2026-09-21T08:00:00Z",
      opened_at: "2026-09-21T09:00:00Z",
      closed_at: "2026-09-21T18:00:00Z",
      published_at: "2026-09-21T19:00:00Z",
      candidates: [],
    };

    mockGetElections.mockResolvedValue([publishedElection]);
    mockGetElection.mockResolvedValue(publishedElection);

    render(<CommandCenterPage />);

    await waitFor(() => {
      expect(screen.getByText(/PUBLISHED — FINAL \/ TERMINAL STATE/i)).toBeDefined();
    });

    // Ensure transition buttons are not displayed
    expect(screen.queryByRole("button", { name: /Close Polls/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Publish Results/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Open Polls/i })).toBeNull();
  });

  it("re-fetches authoritative state and updates UI on 409 transition conflict", async () => {
    const staleElection = {
      id: "EV-2026-001",
      title: "General Election 2026",
      name: "General Election 2026",
      state: "CLOSED",
      configuration_hash: "hash",
      device_count: 3,
      ballot_count: 100,
      candidates: [],
    };

    const authoritativePublished = {
      ...staleElection,
      state: "PUBLISHED",
      published_at: "2026-09-21T19:00:00Z",
    };

    mockGetElections.mockResolvedValue([staleElection]);
    mockGetElection.mockResolvedValueOnce(staleElection); // Initial load

    render(<CommandCenterPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Publish Results/i })).toBeDefined();
    });

    // When clicking publish, backend returns 409 because election is already PUBLISHED
    mockUpdateElectionState.mockRejectedValueOnce(
      new Error("Invalid state transition: PUBLISHED → PUBLISHED")
    );
    // Auto-refetch returns the authoritative state
    mockGetElection.mockResolvedValueOnce(authoritativePublished);
    mockGetElections.mockResolvedValueOnce([authoritativePublished]);

    const publishBtn = screen.getByRole("button", { name: /Publish Results/i });
    fireEvent.click(publishBtn);

    await waitFor(() => {
      // Must display state change notification
      expect(screen.getByText(/Election state changed elsewhere. Current state: PUBLISHED./i)).toBeDefined();
      // Must transition to terminal banner
      expect(screen.getByText(/PUBLISHED — FINAL \/ TERMINAL STATE/i)).toBeDefined();
    });
  });
});
