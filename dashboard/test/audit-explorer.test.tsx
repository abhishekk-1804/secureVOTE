import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import AuditExplorerPage from "@/app/audit/page";
import { api } from "@/lib/api-client";
import { AuditEntryResponse, AuditVerificationResponse } from "@/lib/types";

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
    getAuditLog: vi.fn(),
    verifyAuditChain: vi.fn(),
  },
  isDemoMode: (record: any) => {
    if (record.voter_credential && record.voter_credential.startsWith("VOTER-SERIAL-")) {
      return true;
    }
    if (record.event_data && record.event_data.includes("VOTER-SERIAL-")) {
      return true;
    }
    return false;
  },
}));

const mockAuditEntries: AuditEntryResponse[] = [
  {
    id: 1,
    election_id: "EV-2026-001",
    event_type: "ELECTION_CONFIGURED",
    event_data: '{"title":"General Election"}',
    actor: "admin",
    device_id: null,
    sequence_number: 1,
    timestamp: "2026-09-16T10:00:00Z",
    previous_hash: null,
    entry_hash: "11111111aaaaaaaa11111111aaaaaaaa11111111aaaaaaaa11111111aaaaaaaa",
  },
  {
    id: 2,
    election_id: "EV-2026-001",
    event_type: "SESSION_AUTHORIZED",
    event_data: '{"voter_credential":"VOTER-SERIAL-EVM-001-1","device_id":"EVM-001"}',
    actor: "system",
    device_id: "EVM-001",
    sequence_number: 2,
    timestamp: "2026-09-16T10:05:00Z",
    previous_hash: "11111111aaaaaaaa11111111aaaaaaaa11111111aaaaaaaa11111111aaaaaaaa",
    entry_hash: "22222222bbbbbbbb22222222bbbbbbbb22222222bbbbbbbb22222222bbbbbbbb",
  },
  {
    id: 3,
    election_id: "EV-2026-001",
    event_type: "SESSION_AUTHORIZED",
    event_data: '{"voter_credential":"REAL-VOTER-CRED-999","device_id":"EVM-002"}',
    actor: "system",
    device_id: "EVM-002",
    sequence_number: 3,
    timestamp: "2026-09-16T10:10:00Z",
    previous_hash: "22222222bbbbbbbb22222222bbbbbbbb22222222bbbbbbbb22222222bbbbbbbb",
    entry_hash: "33333333cccccccc33333333cccccccc33333333cccccccc33333333cccccccc",
  },
];

const mockAuditVerification: AuditVerificationResponse = {
  election_id: "EV-2026-001",
  total_entries: 3,
  is_intact: true,
  first_broken_sequence: null,
  details: "Audit chain intact across 3 verified records.",
};

describe("AuditExplorerPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getElections as any).mockResolvedValue([
      { id: "EV-2026-001", title: "General Election 2026", state: "OPEN" },
    ]);
    (api.getAuditLog as any).mockResolvedValue(mockAuditEntries);
    (api.verifyAuditChain as any).mockResolvedValue(mockAuditVerification);
  });

  it("renders audit log and cryptographic chain status", async () => {
    render(<AuditExplorerPage />);

    await waitFor(() => {
      expect(screen.getByText("Cryptographic Chain Intact")).toBeInTheDocument();
    });

    expect(screen.getAllByText("ELECTION_CONFIGURED").length).toBeGreaterThan(0);
    expect(screen.getByText("Total Verified Entries:")).toBeInTheDocument();
  });

  it("surfaces [DEMO-MODE] badge on synthetic session audit records (Phase 2 Continuity)", async () => {
    render(<AuditExplorerPage />);

    await waitFor(() => {
      expect(screen.getAllByText("ELECTION_CONFIGURED").length).toBeGreaterThan(0);
    });

    // The second entry has voter_credential: "VOTER-SERIAL-EVM-001-1"
    const demoBadges = screen.getAllByTestId("demo-mode-badge");
    expect(demoBadges.length).toBe(1);
    expect(demoBadges[0]).toHaveTextContent("[DEMO-MODE]");
  });

  it("filters audit log when checking 'Only [DEMO-MODE]'", async () => {
    render(<AuditExplorerPage />);

    await waitFor(() => {
      expect(screen.getAllByText("ELECTION_CONFIGURED").length).toBeGreaterThan(0);
    });

    const demoCheckbox = screen.getByLabelText(/Only \[DEMO-MODE\]/i);
    fireEvent.click(demoCheckbox);

    // In the table rows, ELECTION_CONFIGURED should be filtered out
    const tableCells = screen.queryAllByRole("cell", { name: "ELECTION_CONFIGURED" });
    expect(tableCells.length).toBe(0);

    // The demo mode entry should still be present
    expect(screen.getByTestId("demo-mode-badge")).toBeInTheDocument();
  });
});
