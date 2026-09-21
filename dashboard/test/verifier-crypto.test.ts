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

  it("Ed25519 checkpoint handles verifier absent vs verifier present correctly", async () => {
    const electionId = "EV-2026-001";
    const candidates = [{ id: "C001", name: "Alice", position: 1 }];
    const configHash = await recomputeConfigHash(electionId, candidates);
    const mHash = await recomputeManifestHash(electionId, 0, { C001: 0 }, {}, "PASSED", "INTACT", configHash);

    const baseExport: ElectionExportResponse = {
      export_version: "1.0",
      generated_at: "2026-09-21T11:00:00Z",
      election: { id: electionId, name: "Test", state: "CLOSED", configuration_hash: configHash } as any,
      candidates: candidates as any,
      devices: [],
      ballots: [],
      audit_log: [],
      manifest: {
        election_id: electionId,
        total_ballots: 0,
        candidate_totals: { C001: 0 },
        device_totals: {},
        reconciliation_status: "PASSED",
        audit_chain_status: "INTACT",
        configuration_hash: configHash,
        manifest_hash: mHash,
        digital_signature: {
          signature: "valid-sig-hex",
          public_key: "valid-pk-hex",
          signed_payload: "canonical-manifest-payload",
        },
      } as any,
    };

    // 1. Without verifier function provided: must be UNCHECKED with exact specification text
    const reportWithoutVerifier = await runCryptographicVerification(baseExport);
    const sigCheck1 = reportWithoutVerifier.checkpoints.find((c) => c.id === "digital_signature");
    expect(sigCheck1?.status).toBe("UNCHECKED");
    expect(sigCheck1?.details).toBe("Signature present — cryptographic signature verification not performed by this browser verifier.");

    // 2. With verifier function returning true: VALID SIGNATURE -> PASSED
    const mockVerifier = vi.fn().mockImplementation(async (payload, sig, pk) => {
      if (sig === "valid-sig-hex" && pk === "valid-pk-hex" && payload === "canonical-manifest-payload") {
        return true;
      }
      return false;
    });

    const reportValidSig = await runCryptographicVerification(baseExport, mockVerifier);
    const sigCheck2 = reportValidSig.checkpoints.find((c) => c.id === "digital_signature");
    expect(sigCheck2?.status).toBe("PASSED");

    // 3. MUTATED SIGNATURE -> FAILED
    const mutatedSigExport = JSON.parse(JSON.stringify(baseExport));
    mutatedSigExport.manifest.digital_signature.signature = "corrupted-sig-hex";
    const reportMutatedSig = await runCryptographicVerification(mutatedSigExport, mockVerifier);
    const sigCheck3 = reportMutatedSig.checkpoints.find((c) => c.id === "digital_signature");
    expect(sigCheck3?.status).toBe("FAILED");
    expect(reportMutatedSig.valid).toBe(false);

    // 4. MUTATED MANIFEST HASH -> FAILED
    const mutatedManifestExport = JSON.parse(JSON.stringify(baseExport));
    mutatedManifestExport.manifest.manifest_hash = "deadbeef00000000000000000000000000000000000000000000000000000000";
    const reportMutatedManifest = await runCryptographicVerification(mutatedManifestExport, mockVerifier);
    const sigCheck4 = reportMutatedManifest.checkpoints.find((c) => c.id === "digital_signature");
    expect(sigCheck4?.status).toBe("FAILED");
    expect(reportMutatedManifest.valid).toBe(false);

    // 5. WRONG PUBLIC KEY -> FAILED
    const wrongPkExport = JSON.parse(JSON.stringify(baseExport));
    wrongPkExport.manifest.digital_signature.public_key = "wrong-pk-hex";
    const reportWrongPk = await runCryptographicVerification(wrongPkExport, mockVerifier);
    const sigCheck5 = reportWrongPk.checkpoints.find((c) => c.id === "digital_signature");
    expect(sigCheck5?.status).toBe("FAILED");
    expect(reportWrongPk.valid).toBe(false);
  });

  describe("Tamper Matrix (Mutations A through M)", () => {
    async function createValidBaseline() {
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

      const mHash = await recomputeManifestHash(
        electionId,
        1,
        { C001: 1, C002: 0 },
        { "EVM-001": 1 },
        "PASSED",
        "INTACT",
        configHash
      );

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
        } as any,
        candidates: candidates as any,
        devices: [{ id: "EVM-001", name: "Unit 1", status: "ACTIVE", election_id: electionId, created_at: "" }],
        ballots: [ballot1],
        audit_log: [audit1],
        manifest: {
          election_id: electionId,
          total_ballots: 1,
          candidate_totals: { C001: 1, C002: 0 },
          device_totals: { "EVM-001": 1 },
          reconciliation_status: "PASSED",
          audit_chain_status: "INTACT",
          configuration_hash: configHash,
          manifest_hash: mHash,
          digital_signature: {
            signature: "sig123",
            public_key: "pk123",
            signed_payload: "payload123",
          },
        } as any,
      };

      const mockVerifier = async (_p: any, s: string, _k?: string) => s === "sig123";
      return { exportData, mockVerifier };
    }

    it("A. ballot candidate_id mutation -> FAILED (ballot_hashes)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.ballots[0].candidate_id = "C002"; // altered vote
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "ballot_hashes")?.status).toBe("FAILED");
    });

    it("B. ballot sequence mutation -> FAILED (device_sequence or ballot_hashes)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.ballots[0].sequence_number = 999;
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "ballot_hashes")?.status).toBe("FAILED");
    });

    it("C. ballot_hash mutation -> FAILED (ballot_hashes)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.ballots[0].ballot_hash = "deadbeef".padEnd(64, "0");
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "ballot_hashes")?.status).toBe("FAILED");
    });

    it("D. candidate position mutation -> FAILED (config_hash)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.candidates[0].position = 99;
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "config_hash")?.status).toBe("FAILED");
    });

    it("E. candidate name mutation -> FAILED (config_hash)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.candidates[0].name = "Altered Name";
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "config_hash")?.status).toBe("FAILED");
    });

    it("F. configuration_hash mutation -> FAILED (config_hash)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.election.configuration_hash = "badhash".padEnd(64, "0");
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "config_hash")?.status).toBe("FAILED");
    });

    it("G. audit event data mutation -> FAILED (audit_chain)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.audit_log[0].event_data = "Tampered event data";
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "audit_chain")?.status).toBe("FAILED");
    });

    it("H. audit previous_hash mutation -> FAILED (audit_chain)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.audit_log[0].previous_hash = "CORRUPTED";
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "audit_chain")?.status).toBe("FAILED");
    });

    it("I. audit entry_hash mutation -> FAILED (audit_chain)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.audit_log[0].entry_hash = "corrupted".padEnd(64, "0");
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "audit_chain")?.status).toBe("FAILED");
    });

    it("J. manifest payload mutation -> FAILED (digital_signature)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.manifest!.total_ballots = 9999;
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "digital_signature")?.status).toBe("FAILED");
    });

    it("K. Ed25519 signature mutation -> FAILED (digital_signature)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.manifest!.digital_signature.signature = "invalid_signature";
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "digital_signature")?.status).toBe("FAILED");
    });

    it("L. device contribution mutation -> FAILED (digital_signature manifest check & reconciliation)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      exportData.manifest!.device_totals["EVM-001"] = 50;
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "digital_signature")?.status).toBe("FAILED");
    });

    it("M. reconciliation total mutation -> FAILED (reconciliation & manifest)", async () => {
      const { exportData, mockVerifier } = await createValidBaseline();
      // Add an extra ballot without updating device or candidate totals
      exportData.ballots.push({
        id: "B2",
        session_id: "S2",
        candidate_id: "C999", // unlisted
        device_id: "EVM-002",
        sequence_number: 1,
        recorded_at: "2026-09-21T10:05:00Z",
        ballot_hash: await recomputeBallotHash("EV-2026-001", {
          session_id: "S2",
          candidate_id: "C999",
          device_id: "EVM-002",
          sequence_number: 1,
          recorded_at: "2026-09-21T10:05:00Z",
        }),
      });
      const res = await runCryptographicVerification(exportData, mockVerifier);
      expect(res.valid).toBe(false);
      expect(res.checkpoints.find((c) => c.id === "reconciliation")?.status).toBe("FAILED");
    });
  });
});
