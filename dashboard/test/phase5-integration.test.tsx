import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import ResultsPage from "@/app/results/page";
import AuditExplorerPage from "@/app/audit/page";
import SecurityCenterPage from "@/app/security/page";
import { api } from "@/lib/api-client";

// Mock AuthContext
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "1", username: "admin", role: "ADMIN", is_active: true, created_at: "" },
    token: "mock-token",
    role: "ADMIN",
    logout: vi.fn(),
  }),
}));

// Mock API client
vi.mock("@/lib/api-client", () => ({
  api: {
    getElections: vi.fn(),
    getResults: vi.fn(),
    runVerification: vi.fn(),
    getSigningPublicKey: vi.fn(),
    signElectionManifest: vi.fn(),
    getElectionAnchors: vi.fn(),
    createElectionAnchor: vi.fn(),
    getAuditLog: vi.fn(),
    verifyAuditChain: vi.fn(),
    exportElection: vi.fn(),
    getHealth: vi.fn(),
    getDevices: vi.fn(),
    getElectionAnomalies: vi.fn(),
    tapRFID: vi.fn(),
  },
  isDemoMode: vi.fn().mockReturnValue(false),
}));

describe("Phase 5 Dashboard Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Digital Signature and Audit Root Anchoring section on Results page", async () => {
    (api.getElections as any).mockResolvedValue([
      { id: "EV-2026-001", title: "General Election 2026", state: "CLOSED" },
    ]);
    (api.getResults as any).mockResolvedValue({
      election_id: "EV-2026-001",
      config_hash_valid: true,
      audit_chain_intact: true,
      reconciliation_passed: true,
      tally_independently_verified: true,
      overall_status: "PASSED",
      details: ["Reconciliation passed."],
      manifest: {
        id: "m-1",
        election_id: "EV-2026-001",
        total_ballots: 10,
        candidate_totals: JSON.stringify({ C001: 6, C002: 4 }),
        device_totals: JSON.stringify({ "EVM-001": 10 }),
        reconciliation_status: "PASSED",
        audit_chain_status: "INTACT",
        configuration_hash: "hash123",
        manifest_hash: "manifesthash456",
        digital_signature: JSON.stringify({
          algorithm: "Ed25519",
          key_id: "ed25519-active-key",
          signature: "deadbeef010203",
        }),
        verified_by: "admin",
        candidate_results: [
          { candidate_id: "C001", candidate_name: "Alice", vote_count: 6, percentage: 60 },
          { candidate_id: "C002", candidate_name: "Bob", vote_count: 4, percentage: 40 },
        ],
      },
    });
    (api.getElectionAnchors as any).mockResolvedValue([
      {
        anchor_id: "anc-001",
        election_id: "EV-2026-001",
        provider: "LOCAL ANCHOR",
        root_hash: "root9999",
        anchored_at: "2026-09-16T12:00:00Z",
        commitment_receipt: { status: "COMMITTED", receipt_id: "rcpt-001" },
      },
    ]);

    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Cryptographic Signing & External Anchoring")).toBeInTheDocument();
      expect(screen.getByText("DIGITALLY SIGNED")).toBeInTheDocument();
      expect(screen.getByText("LOCAL ANCHOR")).toBeInTheDocument();
      expect(screen.getByText("root9999")).toBeInTheDocument();
    });
  });

  it("renders 12-point independent verification checks on Audit page", async () => {
    (api.getElections as any).mockResolvedValue([
      { id: "EV-2026-001", title: "General Election 2026", state: "CLOSED" },
    ]);
    (api.getAuditLog as any).mockResolvedValue([
      { id: 1, sequence_number: 1, event_type: "SYSTEM_INIT", previous_hash: null, entry_hash: "h1" },
    ]);
    (api.verifyAuditChain as any).mockResolvedValue({
      is_intact: true,
      total_entries: 1,
      details: "Audit chain intact.",
    });
    (api.exportElection as any).mockResolvedValue({
      export_version: "1.0.0",
      export_hash: "exphash",
      election: { id: "EV-2026-001", configuration_hash: "confighash" },
      candidates: [{ id: "C001" }],
      devices: [{ id: "EVM-001" }],
      ballots: [{ candidate_id: "C001", device_id: "EVM-001", sequence_number: 1 }],
      audit_log: [{ sequence_number: 1, entry_hash: "h1", previous_hash: null }],
      manifest: { total_ballots: 1, digital_signature: "sig" },
    });

    render(<AuditExplorerPage />);

    await waitFor(() => {
      expect(screen.getByText("Run 12-Point Verifier")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Run 12-Point Verifier"));

    await waitFor(() => {
      expect(screen.getByText("OVERALL PASSED (12/12)")).toBeInTheDocument();
      expect(screen.getByText("1. Export Envelope Integrity")).toBeInTheDocument();
      expect(screen.getByText("7. Zero-Drift Reconciliation")).toBeInTheDocument();
      expect(screen.getByText("11. Ed25519 Digital Signature")).toBeInTheDocument();
    });
  });

  it("renders Advisory Anomaly engine and RFID simulator on Security page", async () => {
    (api.getHealth as any).mockResolvedValue({ status: "healthy", service: "securevote-backend" });
    (api.getDevices as any).mockResolvedValue([]);
    (api.getAuditLog as any).mockResolvedValue([]);
    (api.getElectionAnomalies as any).mockResolvedValue({
      election_id: "EV-2026-001",
      findings_count: 1,
      findings: [
        {
          finding_id: "ano-001",
          election_id: "EV-2026-001",
          rule_id: "TAMPER_CORRELATION",
          category: "SECURITY",
          severity: "HIGH",
          evidence: { switch: "chassis" },
          timestamp: "2026-09-16T12:00:00Z",
          advisory_explanation: "Chassis breach event occurred during election window.",
          requires_human_review: true,
        },
      ],
      status: "ADVISORY_ONLY_DOES_NOT_BLOCK_LIFECYCLE",
    });
    (api.tapRFID as any).mockResolvedValue({
      authenticated: true,
      pseudonym: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
      card_status: "VALID",
      device_id: "EVM-001",
      session_id: "session-token-123",
      notice: "RFID AUTHENTICATION != VOTER ELIGIBILITY: Authenticated and session granted.",
    });

    render(<SecurityCenterPage />);

    await waitFor(() => {
      expect(screen.getByText(/ADVISORY ONLY.*REQUIRES HUMAN REVIEW/i)).toBeInTheDocument();
      expect(screen.getByText("TAMPER_CORRELATION")).toBeInTheDocument();
      expect(screen.getByText("RFID / Contactless Identity Abstraction Simulator")).toBeInTheDocument();
    });

    // Test RFID smartcard tap simulation
    fireEvent.click(screen.getByText("Tap Smartcard"));

    await waitFor(() => {
      expect(screen.getByText("6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b")).toBeInTheDocument();
      expect(screen.getByText("RFID AUTHENTICATION != VOTER ELIGIBILITY: Authenticated and session granted.")).toBeInTheDocument();
    });
  });
});
