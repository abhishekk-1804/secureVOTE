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
        const eData = await api.getElection(electionId, token || undefined);
        setElection(eData);
        const dData = await api.getDevices(electionId, token || undefined);
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

  const handleConfirm = async () => {
    if (state !== "VOTE_CONFIRMED" || !selectedCandidate || !sessionToken) return;

    setState("VOTE_SUBMITTED");
    setLcdMessage("RECORDING VOTE...");

    try {
      const res = await api.castVote({
        session_token: sessionToken,
        candidate_id: selectedCandidate,
        device_id: deviceId,
        sequence_number: sequenceNumber
      });

      setLastVoteHash(res.ballot_hash || "TEST-HASH");
      setState("VOTE_COMPLETE");
      setLcdMessage("VOTE RECORDED");
      setShowVvpat(true);

      setTimeout(() => {
        setShowVvpat(false);
        setState("READY");
        setSessionToken(null);
        setSelectedCandidate(null);
        setSequenceNumber(prev => prev + 1);
        setLcdMessage("READY - AWAITING SESSION");
      }, 5000);

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

  const selectedCandData = election?.candidates?.find(c => c.id === selectedCandidate);

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
            <div className="bg-amber-500 text-slate-900 font-bold px-4 py-1 rounded-sm tracking-widest text-sm shadow-inner">
              SIMULATION
            </div>
          </div>

          <EvmLCD message={lcdMessage} />

          <div className="mt-8 bg-slate-900 p-4 rounded-lg border border-slate-700 flex-1 min-h-[300px]">
            <div className="grid grid-cols-1 gap-3">
              {election?.candidates?.map((c, i) => (
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

        {/* Right Panel */}
        <div className="w-full md:w-80 flex flex-col gap-6">
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
          />
        </div>

        {showVvpat && selectedCandData && (
          <VVPATSlip candidate={selectedCandData} hash={lastVoteHash} />
        )}

      </div>
    </div>
  );
}
