import { describe, it, expect, vi } from "vitest";
import {
  sha256Hex,
  canonicalJson,
  recomputeConfigHash,
  recomputeBallotHash,
  recomputeAuditEntryHash,
  recomputeManifestHash,
  runCryptographicVerification,
} from "@/lib/verifier-crypto";
import { ElectionExportResponse } from "@/lib/types";

describe("verifier-crypto unit tests", () => {
  it("canonicalJson produces deterministic sorted compact JSON", () => {
    const obj1 = { z: 1, a: 2, m: { y: "hello", b: [3, 2, 1] } };
    const obj2 = { a: 2, m: { b: [3, 2, 1], y: "hello" }, z: 1 };
    expect(canonicalJson(obj1)).toBe('{"a":2,"m":{"b":[3,2,1],"y":"hello"},"z":1}');
    expect(canonicalJson(obj1)).toBe(canonicalJson(obj2));
  });

  it("sha256Hex computes accurate SHA-256 digests", async () => {
    const digest = await sha256Hex("hello world");
    // Standard known SHA-256 of "hello world"
    expect(digest).toBe("b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9");
  });

  it("recomputes configuration hash matching position ordering", async () => {
    const candidates = [
      { id: "C002", name: "Bob", position: 2, party: "Party B", symbol: "B" },
      { id: "C001", name: "Alice", position: 1, party: "Party A", symbol: "A" },
    ];
    const hash = await recomputeConfigHash("EV-2026-001", candidates);
    expect(hash).toHaveLength(64);

    // Reversed input candidate array must produce identical hash because position ordering is enforced
    const reversed = [candidates[1], candidates[0]];
    const hash2 = await recomputeConfigHash("EV-2026-001", reversed);
    expect(hash).toBe(hash2);
  });

  it("recomputes ballot hash and detects altered ballot contents", async () => {
    const ballot = {
      id: "B001",
      session_id: "S001",
      candidate_id: "C001",
      device_id: "EVM-001",
      sequence_number: 1,
      recorded_at: "2026-09-21T10:00:00Z",
    };
    const validHash = await recomputeBallotHash("EV-2026-001", ballot);
    expect(validHash).toHaveLength(64);

    const tampered = { ...ballot, candidate_id: "C002" };
    const tamperedHash = await recomputeBallotHash("EV-2026-001", tampered);
    expect(tamperedHash).not.toBe(validHash);
  });

  it("runCryptographicVerification passes on authentic export package", async () => {
    const electionId = "EV-2026-001";
    const candidates = [
      { id: "C001", name: "Alice", position: 1, party: "Party A", symbol: "A" },
      { id: "C002", name: "Bob", position: 2, party: "Party B", symbol: "B" },
    ];
    const configHash = await recomputeConfigHash(electionId, candidates);

    const ballot1 = {
      id: "B1",
      session_id: "S1",
      candidate_id: "C001",
      device_id: "EVM-001",
      sequence_number: 1,
      recorded_at: "2026-09-21T10:00:00Z",
      ballot_hash: "",
    };
    ballot1.ballot_hash = await recomputeBallotHash(electionId, ballot1);

    const ballot2 = {
      id: "B2",
      session_id: "S2",
      candidate_id: "C002",
      device_id: "EVM-001",
      sequence_number: 2,
      recorded_at: "2026-09-21T10:01:00Z",
      ballot_hash: "",
    };
    ballot2.ballot_hash = await recomputeBallotHash(electionId, ballot2);

    const audit1 = {
      id: "A1",
      sequence_number: 1,
      event_type: "POLLS_OPEN",
      event_data: "Polls opened",
      timestamp: "2026-09-21T09:00:00Z",
      previous_hash: "GENESIS",
      entry_hash: "",
    };
    audit1.entry_hash = await recomputeAuditEntryHash(audit1, "GENESIS");

    const audit2 = {
      id: "A2",
      sequence_number: 2,
      event_type: "BALLOT_CAST",
      event_data: "Ballot B1 recorded",
      timestamp: "2026-09-21T10:00:00Z",
      previous_hash: audit1.entry_hash,
      entry_hash: "",
    };
    audit2.entry_hash = await recomputeAuditEntryHash(audit2, audit1.entry_hash);

    const exportData: ElectionExportResponse = {
      export_version: "1.0",
      generated_at: "2026-09-21T11:00:00Z",
      election: {
        id: electionId,
        name: "Test Election",
        description: "Test",
        state: "CLOSED",
        configuration_hash: configHash,
        created_at: "2026-09-21T08:00:00Z",
        opened_at: "2026-09-21T09:00:00Z",
        closed_at: "2026-09-21T11:00:00Z",
        published_at: null,
      },
      candidates,
      devices: [{ id: "EVM-001", name: "Unit 1", status: "ACTIVE", election_id: electionId, created_at: "" }],
      ballots: [ballot1, ballot2],
      audit_log: [audit1, audit2],
      manifest: null,
    };

    const report = await runCryptographicVerification(exportData);
    expect(report.valid).toBe(true);
    expect(report.mismatches).toHaveLength(0);
    expect(report.recountedStats.ballots).toBe(2);
    expect(report.recountedStats.reconciliationDrift).toBe(0);
  });

  it("runCryptographicVerification detects mutated ballot hash", async () => {
    const electionId = "EV-2026-001";
    const candidates = [
      { id: "C001", name: "Alice", position: 1, party: "Party A", symbol: "A" },
    ];
    const configHash = await recomputeConfigHash(electionId, candidates);

    const ballot1 = {
      id: "B1",
      session_id: "S1",
      candidate_id: "C001",
      device_id: "EVM-001",
      sequence_number: 1,
      recorded_at: "2026-09-21T10:00:00Z",
      ballot_hash: "0000000000000000000000000000000000000000000000000000000000000000", // TAMPERED!
    };

    const audit1 = {
      id: "A1",
      sequence_number: 1,
      event_type: "POLLS_OPEN",
      event_data: "Polls opened",
      timestamp: "2026-09-21T09:00:00Z",
      previous_hash: "GENESIS",
      entry_hash: "",
    };
    audit1.entry_hash = await recomputeAuditEntryHash(audit1, "GENESIS");

    const exportData: ElectionExportResponse = {
      export_version: "1.0",
      generated_at: "2026-09-21T11:00:00Z",
      election: {
        id: electionId,
        name: "Test Election",
        state: "CLOSED",
        configuration_hash: configHash,
        created_at: "",
        opened_at: null,
        closed_at: null,
        published_at: null,
      },
      candidates,
      devices: [{ id: "EVM-001", name: "Unit 1", status: "ACTIVE", election_id: electionId, created_at: "" }],
      ballots: [ballot1],
      audit_log: [audit1],
      manifest: null,
    };

    const report = await runCryptographicVerification(exportData);
    expect(report.valid).toBe(false);
    const ballotCheck = report.checkpoints.find((c) => c.id === "ballot_hashes");
    expect(ballotCheck?.status).toBe("FAILED");
    expect(ballotCheck?.errorCount).toBe(1);
    expect(report.mismatches.some((m) => m.includes("Ballot B1 hash mismatch"))).toBe(true);
  });

  it("runCryptographicVerification detects broken audit hash chain link", async () => {
    const electionId = "EV-2026-001";
    const candidates = [
      { id: "C001", name: "Alice", position: 1, party: "Party A", symbol: "A" },
    ];
    const configHash = await recomputeConfigHash(electionId, candidates);

    const audit1 = {
      id: "A1",
      sequence_number: 1,
      event_type: "POLLS_OPEN",
      event_data: "Polls opened",
      timestamp: "2026-09-21T09:00:00Z",
      previous_hash: "GENESIS",
      entry_hash: "",
    };
    audit1.entry_hash = await recomputeAuditEntryHash(audit1, "GENESIS");

    const audit2 = {
      id: "A2",
      sequence_number: 2,
      event_type: "BALLOT_CAST",
      event_data: "Ballot cast",
      timestamp: "2026-09-21T10:00:00Z",
      previous_hash: "deadbeef00000000000000000000000000000000000000000000000000000000", // BROKEN LINK!
      entry_hash: "123456",
    };

    const exportData: ElectionExportResponse = {
      export_version: "1.0",
      generated_at: "2026-09-21T11:00:00Z",
      election: {
        id: electionId,
        name: "Test",
        state: "CLOSED",
        configuration_hash: configHash,
        created_at: "",
        opened_at: null,
        closed_at: null,
        published_at: null,
      },
      candidates,
      devices: [],
      ballots: [],
      audit_log: [audit1, audit2],
      manifest: null,
    };

    const report = await runCryptographicVerification(exportData);
    expect(report.valid).toBe(false);
    const auditCheck = report.checkpoints.find((c) => c.id === "audit_chain");
    expect(auditCheck?.status).toBe("FAILED");
  });
});
