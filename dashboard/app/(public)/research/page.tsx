"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  Cpu,
  Lock,
  Eye,
  EyeOff,
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Zap,
  Layers,
  ArrowRight,
  Database,
  Sliders,
  Check,
  XCircle,
  FileCode,
} from "lucide-react";
import { api } from "@/lib/api-client";

export default function ResearchLabPage() {
  const [activeTab, setActiveTab] = useState<"demo" | "benchmarks" | "architecture">("demo");
  const [electionId, setElectionId] = useState("RESEARCH-DEMO-001");
  const [candidates, setCandidates] = useState(["CANDIDATE-A", "CANDIDATE-B", "CANDIDATE-C", "NOTA"]);
  const [electionInitialized, setElectionInitialized] = useState(false);
  const [keyFingerprint, setKeyFingerprint] = useState("");
  const [publicKeyInfo, setPublicKeyInfo] = useState<any>(null);

  // Ballots state
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(0);
  const [withZkp, setWithZkp] = useState(true);
  const [isEncrypting, setIsEncrypting] = useState(false);
  const [currentArtifact, setCurrentArtifact] = useState<any>(null);
  const [castBallots, setCastBallots] = useState<any[]>([]);

  // Tally state
  const [encryptedTally, setEncryptedTally] = useState<any>(null);
  const [decryptedTally, setDecryptedTally] = useState<any>(null);
  const [isAggregating, setIsAggregating] = useState(false);
  const [isDecrypting, setIsDecrypting] = useState(false);

  // Verifier state
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [tamperSimulated, setTamperSimulated] = useState(false);

  // Benchmark data (authoritative empirical 3-run medians: v3.0 Baseline vs v3.1 ZKP)
  const benchmarkComparisonData = [
    {
      ballots: 10,
      v3Size: "1,973 B",
      v31Size: "6,501 B",
      sizeMultiplier: "3.29x",
      v3Gen: "1.91 s",
      v31Gen: "9.07 s",
      genOverhead: "+376.1%",
      v3Verif: "0.049 s",
      v31Verif: "8.55 s",
      status: "PASSED (11/11)",
    },
    {
      ballots: 50,
      v3Size: "1,973 B",
      v31Size: "6,501 B",
      sizeMultiplier: "3.29x",
      v3Gen: "7.17 s",
      v31Gen: "43.14 s",
      genOverhead: "+501.4%",
      v3Verif: "0.28 s",
      v31Verif: "38.58 s",
      status: "PASSED (11/11)",
    },
    {
      ballots: 100,
      v3Size: "1,974 B",
      v31Size: "6,503 B",
      sizeMultiplier: "3.29x",
      v3Gen: "13.83 s",
      v31Gen: "82.27 s",
      genOverhead: "+494.7%",
      v3Verif: "0.53 s",
      v31Verif: "76.90 s",
      status: "PASSED (11/11)",
    },
  ];

  // Handlers
  const handleInitElection = async () => {
    try {
      const res = await api.initV3Election(electionId, candidates);
      setElectionInitialized(true);
      setKeyFingerprint(res.key_fingerprint);
      setPublicKeyInfo(res.public_key);
      setCastBallots([]);
      setEncryptedTally(null);
      setDecryptedTally(null);
      setVerificationResult(null);
      setTamperSimulated(false);
    } catch (err: any) {
      alert("Failed to initialize: " + (err.message || err));
    }
  };

  const handleEncryptAndCast = async () => {
    if (!electionInitialized) return;
    setIsEncrypting(true);
    try {
      const artifact = await api.encryptV3Ballot(electionId, selectedCandidateIndex, withZkp);
      setCurrentArtifact(artifact);
      await api.castV3Ballot(electionId, artifact);
      const ballotsRes = await api.getV3Ballots(electionId);
      setCastBallots(ballotsRes.ballots || []);
      setVerificationResult(null);
    } catch (err: any) {
      alert("Encryption / Cast error: " + (err.message || err));
    } finally {
      setIsEncrypting(false);
    }
  };

  const handleAggregate = async () => {
    setIsAggregating(true);
    try {
      const res = await api.aggregateV3Tally(electionId);
      setEncryptedTally(res.encrypted_tally);
    } catch (err: any) {
      alert("Aggregation error: " + (err.message || err));
    } finally {
      setIsAggregating(false);
    }
  };

  const handleDecrypt = async () => {
    setIsDecrypting(true);
    try {
      const res = await api.decryptV3Tally(electionId);
      setDecryptedTally(res);
    } catch (err: any) {
      alert("Decryption error: " + (err.message || err));
    } finally {
      setIsDecrypting(false);
    }
  };

  const handleVerify = async () => {
    setIsVerifying(true);
    try {
      const pkg = await api.exportV3Package(electionId);
      if (tamperSimulated && pkg.ballots && pkg.ballots.length > 0) {
        // Mutate first slot C1 in first ballot to simulate tamper
        pkg.ballots[0].encrypted_vote.slots[0].c1.x = "0000000000000000000000000000000000000000000000000000000000000001";
      }
      const res = await api.verifyV3Package(pkg);
      setVerificationResult(res);
    } catch (err: any) {
      alert("Verification error: " + (err.message || err));
    } finally {
      setIsVerifying(false);
    }
  };

  const toggleTamper = () => {
    setTamperSimulated(!tamperSimulated);
    setVerificationResult(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400">
                <ShieldCheck className="w-7 h-7" />
              </div>
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                  SecureVOTE 3.1 Research Lab
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-950 border border-indigo-500/40 text-indigo-400 font-mono">
                    ZKP Ballot Validity · CDS94
                  </span>
                </h1>
                <p className="text-sm text-slate-400 mt-1">
                  Exponential ElGamal over NIST P-256 (secp256r1) with Non-Interactive Zero-Knowledge Ballot Validity Proofs
                </p>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1 text-sm font-medium">
            <button
              onClick={() => setActiveTab("demo")}
              className={`px-4 py-2 rounded-md transition-all ${
                activeTab === "demo" ? "bg-emerald-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              Interactive Pipeline
            </button>
            <button
              onClick={() => setActiveTab("benchmarks")}
              className={`px-4 py-2 rounded-md transition-all ${
                activeTab === "benchmarks" ? "bg-emerald-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              Empirical Benchmarks
            </button>
            <button
              onClick={() => setActiveTab("architecture")}
              className={`px-4 py-2 rounded-md transition-all ${
                activeTab === "architecture" ? "bg-emerald-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              Security Analysis & Gaps
            </button>
          </div>
        </div>

        {/* TAB 1: INTERACTIVE PIPELINE */}
        {activeTab === "demo" && (
          <div className="space-y-8">
            {/* Step 1: Election Initialization */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-emerald-400" />
                  <h2 className="text-lg font-semibold text-white">Stage 1: Cryptographic Key Setup</h2>
                </div>
                {!electionInitialized ? (
                  <button
                    onClick={handleInitElection}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" /> Initialize Research Election
                  </button>
                ) : (
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono bg-emerald-950/60 px-3 py-1 rounded-full border border-emerald-500/30">
                    <CheckCircle2 className="w-3.5 h-3.5" /> ACTIVE (secp256r1)
                  </span>
                )}
              </div>

              {electionInitialized && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono bg-slate-950/80 p-4 rounded-lg border border-slate-800/80">
                  <div>
                    <span className="text-slate-500 block mb-1">ELECTION ID</span>
                    <span className="text-slate-200">{electionId}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-1">CURVE & PROTOCOL</span>
                    <span className="text-emerald-400">NIST P-256 (secp256r1) · SECUREVOTE31</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-1">PUBLIC KEY FINGERPRINT (SHA-256)</span>
                    <span className="text-amber-400 truncate block">{keyFingerprint}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Step 2: Encrypted Ballot Creation + ZKP */}
            {electionInitialized && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Lock className="w-5 h-5 text-indigo-400" />
                    <h2 className="text-lg font-semibold text-white">Stage 2: Confidential Voter Choice & ZK Validity Proof</h2>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    Ballots Cast: {castBallots.length}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Candidate Selection */}
                  <div className="space-y-4">
                    <div>
                      <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Select Candidate Choice</label>
                      <div className="grid grid-cols-2 gap-2">
                        {candidates.map((cand, idx) => (
                          <button
                            key={cand}
                            onClick={() => setSelectedCandidateIndex(idx)}
                            className={`p-3 rounded-lg border text-left font-mono text-sm transition-all ${
                              selectedCandidateIndex === idx
                                ? "bg-indigo-950/80 border-indigo-500 text-white"
                                : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                            }`}
                          >
                            <div className="text-xs text-slate-500">Slot {idx}</div>
                            <div className="font-bold mt-0.5">{cand}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* ZKP Generation Toggle */}
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
                      <div>
                        <div className="text-xs font-bold text-slate-200">Zero-Knowledge Proof (CDS94)</div>
                        <div className="text-[11px] text-slate-400">Proves ∀j: v_j ∈ {'{0,1}'} ∧ Σv_j = 1 without revealing choice</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={withZkp}
                          onChange={(e) => setWithZkp(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                      </label>
                    </div>

                    <button
                      onClick={handleEncryptAndCast}
                      disabled={isEncrypting}
                      className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition flex items-center justify-center gap-2"
                    >
                      {isEncrypting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
                      Encrypt Choice {withZkp ? "+ Generate ZK Validity Proof" : "(Plaintext Slot Mode)"} & Cast
                    </button>
                  </div>

                  {/* Encryption Artifact Inspection */}
                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3 font-mono text-xs">
                    <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2">
                      <span>BALLOT ENCRYPTION ARTIFACT</span>
                      <span className="text-emerald-400">
                        {currentArtifact?.proof ? "One-Hot Vector + NIZK Proof" : "One-Hot Vector"}
                      </span>
                    </div>

                    {currentArtifact ? (
                      <div className="space-y-2 text-slate-300">
                        <div><span className="text-slate-500">Artifact UUID:</span> {currentArtifact.artifact_id}</div>
                        <div><span className="text-slate-500">Commitment:</span> <span className="text-amber-400">{currentArtifact.commitment.slice(0, 32)}...</span></div>
                        <div><span className="text-slate-500">Artifact Hash:</span> <span className="text-cyan-400">{currentArtifact.artifact_hash.slice(0, 32)}...</span></div>

                        {/* ZKP Proof Details */}
                        {currentArtifact.proof ? (
                          <div className="p-2.5 bg-indigo-950/40 rounded border border-indigo-900/60 space-y-1 text-[11px]">
                            <div className="text-indigo-400 font-bold flex items-center gap-1.5">
                              <CheckCircle2 className="w-3.5 h-3.5" /> NIZK VALIDITY PROOF (CDS94 + Chaum-Pedersen)
                            </div>
                            <div className="text-slate-400">
                              • Protocol Version: <span className="text-slate-200">{currentArtifact.proof.protocol_version}</span>
                            </div>
                            <div className="text-slate-400">
                              • Disjunctive Slot Proofs: <span className="text-indigo-300">{currentArtifact.proof.slot_proofs?.length || 4} proofs (∀j: v_j ∈ {'{0,1}'})</span>
                            </div>
                            <div className="text-slate-400 truncate">
                              • Sum Equality Proof: <span className="text-indigo-300">PoK(R: ΣC_1 = R·G ∧ ΣC_2 - G = R·Y)</span>
                            </div>
                          </div>
                        ) : (
                          <div className="p-2 bg-slate-900 rounded border border-slate-800 text-slate-500 text-[11px]">
                            No ZK validity proof attached (Legacy v3.0 mode).
                          </div>
                        )}

                        <div className="pt-2 text-slate-400 border-t border-slate-800/80">
                          <span>Ciphertext Slots ({currentArtifact.encrypted_vote.slots.length} curve points):</span>
                          <div className="mt-1 space-y-1 text-[11px] text-slate-500">
                            {currentArtifact.encrypted_vote.slots.map((s: any, idx: number) => (
                              <div key={idx} className="truncate">
                                Slot {idx}: C1=({s.c1.x.slice(0, 10)}...), C2=({s.c2.x.slice(0, 10)}...)
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-slate-500 py-8 text-center">
                        Select a candidate and click "Encrypt Choice" to observe one-hot encryption and ZK proof generation.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Homomorphic Aggregation & Decryption */}
            {castBallots.length > 0 && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Layers className="w-5 h-5 text-amber-400" />
                    <h2 className="text-lg font-semibold text-white">Stage 3: Additive Homomorphic Tally & Discrete-Log Decryption</h2>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={handleAggregate}
                      disabled={isAggregating}
                      className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition flex items-center gap-1.5"
                    >
                      <Layers className="w-3.5 h-3.5" /> Aggregate Ciphertexts
                    </button>
                    {encryptedTally && (
                      <button
                        onClick={handleDecrypt}
                        disabled={isDecrypting}
                        className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition flex items-center gap-1.5"
                      >
                        <Zap className="w-3.5 h-3.5" /> Decrypt Aggregate
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs">
                  {/* Encrypted Aggregate */}
                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                    <div className="text-slate-400 font-semibold mb-2">HOMOMORPHIC AGGREGATE TALLY</div>
                    {encryptedTally ? (
                      <div className="space-y-2 text-slate-300">
                        <div><span className="text-slate-500">Ballot Count:</span> {castBallots.length}</div>
                        <div><span className="text-slate-500">Tally Commitment:</span> <span className="text-amber-400">{encryptedTally.commitment ? encryptedTally.commitment.slice(0, 24) : ""}...</span></div>
                        <div className="text-emerald-400 pt-1">Σ Enc(B_i) computed via curve point addition without ballot decryption</div>
                      </div>
                    ) : (
                      <div className="text-slate-500 py-6 text-center">Click "Aggregate Ciphertexts" to sum encrypted ballots.</div>
                    )}
                  </div>

                  {/* Decrypted Tally */}
                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                    <div className="text-slate-400 font-semibold mb-2">DECRYPTED RESULTS & RECONCILIATION</div>
                    {decryptedTally ? (
                      <div className="space-y-2 text-slate-200">
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(decryptedTally.candidate_tallies || {}).map(([c, count]) => (
                            <div key={c} className="p-2 bg-slate-900 rounded border border-slate-800 flex justify-between">
                              <span>{c}:</span>
                              <span className="font-bold text-emerald-400">{count as number}</span>
                            </div>
                          ))}
                        </div>
                        <div className="pt-2 border-t border-slate-800 flex justify-between text-slate-400">
                          <span>Reconciliation Status:</span>
                          <span className="text-emerald-400 font-bold">{decryptedTally.reconciliation_status}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="text-slate-500 py-6 text-center">Click "Decrypt Aggregate" to recover plaintext sums.</div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 4: Standalone Independent Verifier */}
            {castBallots.length > 0 && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    <h2 className="text-lg font-semibold text-white">Stage 4: Independent 11-Checkpoint Verifier (With ZKP Proofs)</h2>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={toggleTamper}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition border ${
                        tamperSimulated
                          ? "bg-rose-950 border-rose-500 text-rose-300"
                          : "bg-slate-950 border-slate-700 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {tamperSimulated ? "⚠️ Tamper Simulation: ACTIVE" : "Simulate Mutation Attack"}
                    </button>
                    <button
                      onClick={handleVerify}
                      disabled={isVerifying}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-2"
                    >
                      {isVerifying ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                      Run Independent Verification
                    </button>
                  </div>
                </div>

                {tamperSimulated && (
                  <div className="mb-4 p-3 bg-rose-950/50 border border-rose-800 rounded-lg text-xs text-rose-300 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>Attack Simulation: A ciphertext coordinate in ballot 0 has been maliciously modified. The verifier will catch curve, hash, and ZK proof invalidation.</span>
                  </div>
                )}

                {verificationResult && (
                  <div className="space-y-4 font-mono text-xs">
                    <div className={`p-4 rounded-lg border font-bold text-sm flex items-center justify-between ${
                      verificationResult.verified
                        ? "bg-emerald-950/60 border-emerald-500/50 text-emerald-300"
                        : "bg-rose-950/60 border-rose-500/50 text-rose-300"
                    }`}>
                      <span>
                        INDEPENDENT VERIFICATION: {verificationResult.verified ? "PASSED (ALL CHECKPOINTS SATISFIED)" : "FAILED (TAMPER OR FRAUD DETECTED)"}
                      </span>
                      <span>Passed: {verificationResult.checkpoints_passed} / {verificationResult.checkpoints_total}</span>
                    </div>

                    {/* Diagnostic Summary Badges */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px]">
                      <div className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center justify-between">
                        <span className="text-slate-400">Curve Validity</span>
                        <span className={verificationResult.ciphertext_structurally_valid ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                          {verificationResult.ciphertext_structurally_valid ? "VALID" : "INVALID"}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center justify-between">
                        <span className="text-slate-400">Commitment Integrity</span>
                        <span className={verificationResult.commitment_valid ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                          {verificationResult.commitment_valid ? "VALID" : "INVALID"}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center justify-between">
                        <span className="text-slate-400">ZK Ballot Validity</span>
                        <span className={verificationResult.ballot_validity_valid ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                          {verificationResult.ballot_validity_valid ? "PROVEN" : "FAILED"}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center justify-between">
                        <span className="text-slate-400">Homomorphic Sum</span>
                        <span className={verificationResult.ballot_aggregation_valid ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                          {verificationResult.ballot_aggregation_valid ? "MATCH" : "MISMATCH"}
                        </span>
                      </div>
                    </div>

                    {/* Checkpoint Detail List */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
                      {verificationResult.checkpoints.map((cp: any) => (
                        <div
                          key={cp.checkpoint}
                          className={`p-2.5 rounded border text-xs flex items-center justify-between ${
                            cp.status === "PASSED"
                              ? "bg-slate-950 border-emerald-900/40 text-slate-300"
                              : "bg-rose-950/40 border-rose-800/80 text-rose-300"
                          }`}
                        >
                          <span className="truncate pr-2">{cp.checkpoint}</span>
                          <span className={cp.status === "PASSED" ? "text-emerald-400 font-bold shrink-0" : "text-rose-400 font-bold shrink-0"}>
                            {cp.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        )}

        {/* TAB 2: EMPIRICAL BENCHMARKS */}
        {activeTab === "benchmarks" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="w-5 h-5 text-cyan-400" />
                <h2 className="text-lg font-semibold text-white">Empirical Cryptographic Benchmark: v3.0 vs v3.1 ZKP</h2>
              </div>
              <p className="text-sm text-slate-400 mb-6">
                Comparative overhead evaluation between SecureVOTE 3.0 (baseline Exponential ElGamal without validity proof) and SecureVOTE 3.1 (with non-interactive CDS94 disjunctive proofs and Chaum-Pedersen sum equality proof). Measured over NIST P-256 (secp256r1) with 4 candidate slots.
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 bg-slate-950/60">
                      <th className="p-3">Scale (Ballots)</th>
                      <th className="p-3">v3.0 Ballot Size</th>
                      <th className="p-3">v3.1 ZKP Ballot Size</th>
                      <th className="p-3">Size Multiplier</th>
                      <th className="p-3">v3.0 Generation</th>
                      <th className="p-3">v3.1 Generation</th>
                      <th className="p-3">v3.0 Verification</th>
                      <th className="p-3">v3.1 Verification</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {benchmarkComparisonData.map((row) => (
                      <tr key={row.ballots} className="hover:bg-slate-900/40 transition">
                        <td className="p-3 font-bold text-white">{row.ballots.toLocaleString()}</td>
                        <td className="p-3 text-slate-300">{row.v3Size}</td>
                        <td className="p-3 text-indigo-400 font-bold">{row.v31Size}</td>
                        <td className="p-3 text-amber-400">{row.sizeMultiplier}</td>
                        <td className="p-3 text-slate-300">{row.v3Gen}</td>
                        <td className="p-3 text-cyan-400">{row.v31Gen}</td>
                        <td className="p-3 text-slate-300">{row.v3Verif}</td>
                        <td className="p-3 text-purple-400">{row.v31Verif}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-400 font-bold">
                            {row.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-6 p-4 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-400 space-y-1.5 font-mono">
                <div>• <strong>Methodology:</strong> Values report median of 3 independent empirical repetitions per scale (seeds 42, 143, 244) with gc.collect() isolation. Raw run variability and evidence recorded in <code className="text-cyan-400">evidence/v3_1_zkp_benchmark_results.json</code>.</div>
                <div>• <strong>Ballot Size Overhead:</strong> Fixed +4,528 to +4,530 bytes per 4-candidate ballot (~6,503 B vs ~1,974 B, a ~3.29x overhead factor).</div>
                <div>• <strong>Proof Complexity:</strong> Exactly 4 CDS94 slot proofs (each containing 4 curve points and 4 scalar responses) + 1 Chaum-Pedersen sum equality proof (2 curve points + 1 scalar response).</div>
                <div>• <strong>Verification Workload:</strong> Exactly 8k + 4 = 36 curve scalar multiplications per ballot (8 per candidate slot for disjunctive proof + 4 for aggregate sum equality proof with k=4) to verify ∀j: v_j ∈ {'{0,1}'} and Σv_j = 1 under random oracle heuristic.</div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: SECURITY ANALYSIS & GAPS */}
        {activeTab === "architecture" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Lock className="w-5 h-5 text-emerald-400" />
                  Cryptographic Assurance & Ground Truth Status Matrix
                </h2>
                <p className="text-sm text-slate-400 mt-1">
                  Rigorous classification of implemented properties versus remaining research gaps in SecureVOTE 3.1.
                </p>
              </div>

              {/* Status Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 bg-slate-950/60">
                      <th className="p-3">Property / Capability</th>
                      <th className="p-3">Status</th>
                      <th className="p-3">Technical Description & Scope</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    <tr>
                      <td className="p-3 font-bold text-white">Exponential ElGamal Encryption</td>
                      <td className="p-3"><span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-400 font-bold">IMPLEMENTED</span></td>
                      <td className="p-3 text-slate-400">Additive homomorphic encryption over NIST P-256 with component-wise point addition.</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Zero-Knowledge Ballot Validity</td>
                      <td className="p-3"><span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-400 font-bold">IMPLEMENTED</span></td>
                      <td className="p-3 text-slate-400">Non-interactive Fiat-Shamir CDS94 disjunctive proofs for slots and Chaum-Pedersen sum equality.</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Recorded-as-Cast (Public Ledger)</td>
                      <td className="p-3"><span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-400 font-bold">IMPLEMENTED</span></td>
                      <td className="p-3 text-slate-400">Domain-separated SHA-256 ballot commitments and artifact hashes published in verifier export package.</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Tallied-as-Recorded (Universal Verifiability)</td>
                      <td className="p-3"><span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-400 font-bold">IMPLEMENTED</span></td>
                      <td className="p-3 text-slate-400">Decoupled standalone verifier validates all curve points, commitments, ZK validity proofs, and tally sum.</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Formal Machine-Checked Proof</td>
                      <td className="p-3"><span className="px-2 py-0.5 rounded bg-amber-950 border border-amber-500/40 text-amber-400 font-bold">EXPERIMENTAL</span></td>
                      <td className="p-3 text-slate-400">Adheres to peer-reviewed literature (CDS94, Chaum-Pedersen), but lacks machine verification (e.g. EasyCrypt).</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Threshold Decryption / DKG</td>
                      <td className="p-3"><span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400 font-bold">NOT IMPLEMENTED</span></td>
                      <td className="p-3 text-slate-400">Single-authority private key held in server memory; (t, n) Distributed Key Generation planned for 3.2.</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Cast-as-Intended (Benaloh Audit)</td>
                      <td className="p-3"><span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400 font-bold">NOT IMPLEMENTED</span></td>
                      <td className="p-3 text-slate-400">Terminal computes ciphertext; voter cannot independently verify encryption without trusting terminal software.</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Mix-Net / Timing Anonymity</td>
                      <td className="p-3"><span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400 font-bold">NOT IMPLEMENTED</span></td>
                      <td className="p-3 text-slate-400">Ballots stored without voter IDs, but arrival timestamps create timing correlation risk without mix-nets.</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Research Guardrail Notice */}
              <div className="p-4 bg-amber-950/40 border border-amber-800/80 rounded-lg text-xs text-amber-300 space-y-2">
                <div className="font-bold flex items-center gap-1.5 text-amber-200">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                  SCIENTIFIC DISCLAIMER: SCOPE OF VERIFIABILITY CLAIMS
                </div>
                <p>
                  SecureVOTE 3.1 does <strong>NOT</strong> claim full End-to-End Verifiability (E2E-V). While universal verifiability ("Tallied as Recorded") and ballot validity ("Well-Formed Choice") are computationally sound under standard cryptographic assumptions and independently verified, individual verifiability ("Cast as Intended" via Benaloh challenge) and threshold distributed decryption are ongoing research milestones.
                </p>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
