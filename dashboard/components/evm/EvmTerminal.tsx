"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { ElectionResponse, DeviceResponse, CandidateResponse } from "@/lib/types";
import { useAuth } from "@/context/AuthContext";
import EvmLCD from "./EvmLCD";
import EvmCandidateButton from "./EvmCandidateButton";
import EvmControlPanel from "./EvmControlPanel";
import VVPATSlip from "./VVPATSlip";
import EvmStatusPanel from "./EvmStatusPanel";

type EvmState =
  | "IDLE"
  | "READY"
  | "SESSION_AUTHORIZED"
  | "CANDIDATE_SELECTION"
  | "VOTE_CONFIRMED"
  | "VOTE_SUBMITTED"
  | "VOTE_COMPLETE"
  | "ERROR";

export default function EvmTerminal({ deviceId, electionId }: { deviceId: string, electionId: string }) {
  const { token, login } = useAuth();
  const [election, setElection] = useState<ElectionResponse | null>(null);
  const [device, setDevice] = useState<DeviceResponse | null>(null);
  const [state, setState] = useState<EvmState>("IDLE");
  const [lcdMessage, setLcdMessage] = useState("INITIALIZING...");
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);
  const [sequenceNumber, setSequenceNumber] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [showVvpat, setShowVvpat] = useState(false);
  const [lastVoteHash, setLastVoteHash] = useState("");

  useEffect(() => {
    const init = async () => {
      try {
        let eData: any = null;
        if (token) {
          try {
            eData = await api.getElection(electionId, token);
          } catch {
            // fallback to public transparency
          }
        }
        if (!eData) {
          const pub = await api.getTransparencyOverview(electionId);
          const cands = await api.getTransparencyCandidates(electionId);
          eData = {
            id: pub.election_id,
            name: pub.election_name,
            title: pub.election_name,
            state: pub.state,
            candidates: cands,
          };
        }
        if (!eData.candidates || eData.candidates.length === 0) {
          try {
            eData.candidates = await api.getTransparencyCandidates(electionId);
          } catch {}
        }
        setElection(eData);

        let dData: DeviceResponse[] = [];
        if (token) {
          try {
            dData = await api.getDevices(electionId, token);
          } catch {
            // fallback
          }
        }
        if (dData.length === 0) {
          dData = await api.getTransparencyDevices(electionId);
        }
        const dev = dData.find(d => d.id === deviceId);
        if (!dev) throw new Error("DEVICE_NOT_FOUND");
        setDevice(dev);
        setSequenceNumber(dev.last_sequence_number + 1);

        if (eData.state !== "OPEN") throw new Error("POLLING_CLOSED");
        if (dev.status !== "ACTIVE") throw new Error("DEVICE_INACTIVE");

        setState("READY");
        setLcdMessage("READY - AWAITING SESSION");
      } catch (err: any) {
        setState("ERROR");
        setLcdMessage(err.message || "INITIALIZATION FAILED");
      }
    };
    init();
  }, [electionId, deviceId, token]);

  const handleInitSession = async (authCreds?: { u: string, p: string }) => {
    try {
      let currentToken = token;
      if (!currentToken && authCreds) {
        setLcdMessage("AUTHENTICATING...");
        const t = await api.login(authCreds.u, authCreds.p);
        currentToken = t.access_token;
      }

      if (!currentToken) {
        if (isMockPoll) {
          setState("CANDIDATE_SELECTION");
          setLcdMessage("SELECT CANDIDATE");
          return;
        }
        setLcdMessage("OFFICER LOGIN REQUIRED");
        return;
      }

      setLcdMessage("AUTHORIZING SESSION...");
      const voterCred = `VOTER-EVM-${Date.now()}`;
      const res = await api.authorizeSession(electionId, { voter_credential: voterCred, device_id: deviceId }, currentToken);

      setSessionToken(res.session_token);
      setState("CANDIDATE_SELECTION");
      setLcdMessage("SELECT CANDIDATE");
    } catch (err: any) {
      setLcdMessage("SESSION FAILED");
      setTimeout(() => setLcdMessage("READY - AWAITING SESSION"), 3000);
    }
  };

  const handleCandidateSelect = (id: string) => {
    if (state !== "CANDIDATE_SELECTION" && state !== "VOTE_CONFIRMED") return;
    setSelectedCandidate(id);
    setState("VOTE_CONFIRMED");
    setLcdMessage("CANDIDATE SELECTED");
  };

  const [isMockPoll, setIsMockPoll] = useState(false);
  const [mockVotes, setMockVotes] = useState<Record<string, number>>({});
  const [mockCleared, setMockCleared] = useState(false);

  const totalMockVotes = Object.values(mockVotes).reduce((a, b) => a + b, 0);

  const handleClearMockPoll = () => {
    setMockVotes({});
    setMockCleared(true);
    setLcdMessage("UI DIAGNOSTIC MODE - DATA CLEARED");
    setTimeout(() => {
      setLcdMessage(isMockPoll ? "UI DIAGNOSTIC MODE - READY" : "READY - AWAITING SESSION");
    }, 3000);
  };

function playEvmBeep() {
  try {
    if (typeof window !== "undefined") {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(1000, ctx.currentTime);
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 1.2);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 1.2);
      }
    }
  } catch {
    // Ignore in audio-restricted environments
  }
}

  const rawCandidates = election?.candidates || [];
  const hasNota = rawCandidates.some(
    (c) => c.name.toUpperCase().includes("NOTA") || c.id.toUpperCase().includes("NOTA")
  );
  const candidateSlate: CandidateResponse[] = hasNota
    ? rawCandidates
    : [
        ...rawCandidates,
        {
          id: "C005",
          name: "None of the Above (NOTA)",
          party: "None of the Above",
          symbol: "NOTA",
          position: rawCandidates.length + 1,
          election_id: electionId,
        } as CandidateResponse,
      ];

  const handleConfirm = async () => {
    if (state !== "VOTE_CONFIRMED" || !selectedCandidate) return;

    if (isMockPoll) {
      setState("VOTE_SUBMITTED");
      setLcdMessage("UI DIAGNOSTIC — LOCAL ONLY (NO BACKEND)");
      setMockVotes(prev => ({
        ...prev,
        [selectedCandidate]: (prev[selectedCandidate] || 0) + 1,
      }));
      playEvmBeep();
      setLastVoteHash(`DIAG-SLIP-${Date.now().toString(16).toUpperCase()}`);
      setState("VOTE_COMPLETE");
      setShowVvpat(true);

      setTimeout(() => {
        setShowVvpat(false);
        setState("READY");
        setSelectedCandidate(null);
        setLcdMessage("UI DIAGNOSTIC MODE - READY");
      }, 7000);
      return;
    }

    if (!sessionToken) return;

    setState("VOTE_SUBMITTED");
    setLcdMessage("RECORDING VOTE...");

    try {
      const res = await api.castVote({
        session_token: sessionToken,
        candidate_id: selectedCandidate,
        device_id: deviceId,
        sequence_number: sequenceNumber
      });

      playEvmBeep();
      setLastVoteHash(res.ballot_hash || "TEST-HASH");
      setState("VOTE_COMPLETE");
      setLcdMessage("VOTE RECORDED - VVPAT SLIP PRINTED");
      setShowVvpat(true);

      setTimeout(() => {
        setShowVvpat(false);
        setState("READY");
        setSessionToken(null);
        setSelectedCandidate(null);
        setSequenceNumber(prev => prev + 1);
        setLcdMessage("READY - AWAITING SESSION");
      }, 7000);

    } catch (err: any) {
      setLcdMessage("VOTE REJECTED");
      setTimeout(() => {
        setState("CANDIDATE_SELECTION");
        setLcdMessage("SELECT CANDIDATE");
      }, 3000);
    }
  };

  const handleCancel = () => {
    if (state === "VOTE_CONFIRMED") {
      setSelectedCandidate(null);
      setState("CANDIDATE_SELECTION");
      setLcdMessage("SELECT CANDIDATE");
    }
  };

  const selectedCandData = candidateSlate.find(c => c.id === selectedCandidate);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-8 select-none">
      <div className="w-full max-w-5xl bg-slate-800 rounded-xl shadow-2xl border-4 border-slate-700 p-8 flex flex-col md:flex-row gap-8 relative overflow-hidden">

        {/* Main Panel */}
        <div className="flex-1 flex flex-col">
          <div className="flex justify-between items-center border-b-2 border-slate-700 pb-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-200 tracking-wider">EVM DIGITAL TWIN</h1>
              <div className="text-slate-400 font-mono text-sm mt-1">{deviceId} | {election?.title || "Loading..."}</div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  const nextMode = !isMockPoll;
                  setIsMockPoll(nextMode);
                  setState("READY");
                  setSelectedCandidate(null);
                  setLcdMessage(nextMode ? "UI DIAGNOSTIC MODE - READY" : "READY - AWAITING SESSION");
                }}
                className={`px-3 py-1 rounded text-xs font-bold transition-all border ${
                  isMockPoll
                    ? "bg-amber-500 text-slate-950 border-amber-400 font-mono shadow-md"
                    : "bg-slate-700 text-slate-300 border-slate-600 hover:bg-slate-600"
                }`}
              >
                {isMockPoll ? "UI DIAGNOSTIC: ACTIVE" : "ENABLE UI DIAGNOSTIC"}
              </button>
              <div className="bg-amber-500 text-slate-950 font-bold px-3 py-1 rounded-sm tracking-widest text-xs shadow-inner">
                SIMULATION
              </div>
            </div>
          </div>

          {isMockPoll && (
            <div className="mb-4 bg-rose-950/40 border-2 border-rose-500/50 rounded-lg p-3 text-xs flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-bold text-rose-400 text-sm tracking-widest">⚠ UI DIAGNOSTIC MODE</span>
                  <span className="text-slate-300 font-mono ml-2">{totalMockVotes} Local Test Interactions</span>
                </div>
                <button
                  type="button"
                  onClick={handleClearMockPoll}
                  className="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded text-[11px] transition-colors"
                >
                  Clear Data (CLR)
                </button>
              </div>
              <div className="text-rose-300 text-[10px] font-mono mt-1 border-t border-rose-500/30 pt-1">
                Local-only test interaction • No ballot is persisted to the election backend
              </div>
            </div>
          )}

          <EvmLCD message={lcdMessage} />

          <div className="mt-6 bg-slate-900 p-4 rounded-lg border border-slate-700 flex-1 min-h-[300px]">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-800 text-[11px] font-mono text-slate-400">
              <span className="font-semibold text-slate-300">BALLOT UNIT (BU) — CANDIDATE SLATE</span>
              <span>RULE 49B COMPLIANT WITH NOTA</span>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {candidateSlate.map((c) => (
                <EvmCandidateButton
                  key={c.id}
                  candidate={c}
                  isActive={state === "CANDIDATE_SELECTION" || state === "VOTE_CONFIRMED"}
                  isSelected={selectedCandidate === c.id}
                  onClick={() => handleCandidateSelect(c.id)}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel: Control Unit & Status */}
        <div className="w-full md:w-80 flex flex-col gap-6">
          <div className="text-[11px] font-mono text-slate-400 font-semibold tracking-wider border-b border-slate-700 pb-1">
            CONTROL UNIT (CU) TWIN
          </div>
          <EvmStatusPanel
            state={state}
            sequenceNumber={sequenceNumber}
            isElectionOpen={election?.state === "OPEN"}
          />
          <EvmControlPanel
            onInitSession={handleInitSession}
            onConfirm={handleConfirm}
            onCancel={handleCancel}
            canInit={state === "READY"}
            canConfirm={state === "VOTE_CONFIRMED"}
            canCancel={state === "VOTE_CONFIRMED"}
            isAuthed={!!token}
            isMockPoll={isMockPoll}
          />
        </div>

        {showVvpat && selectedCandData && (
          <VVPATSlip candidate={selectedCandData} hash={lastVoteHash} isMockPoll={isMockPoll} />
        )}

      </div>
    </div>
  );
}
