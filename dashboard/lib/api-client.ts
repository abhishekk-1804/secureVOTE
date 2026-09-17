/**
 * SecureVOTE Typed API Client.
 *
 * Implements authoritative backend contract, auth header injection,
 * and 401 redirect handling.
 */

import {
  AuditEntryResponse,
  AuditVerificationResponse,
  CandidateCreate,
  CandidateResponse,
  DeviceRegister,
  DeviceResponse,
  DeviceStatus,
  ElectionResponse,
  ElectionState,
  HealthCheckResponse,
  TokenResponse,
  UserResponse,
  VerificationResponse,
  WsTicketResponse,
  ElectionExportResponse,
  PublicKeyInfoResponse,
  SignedManifestResponse,
  AuditAnchorResponse,
  AdvisoryFindingsResponse,
  RFIDTapRequest,
  RFIDTapResponse,
  VoterResponse,
  EligibilityCheckResponse,
  PollingStationResponse,
  ComplaintResponse,
  SimulationResponse,
  TransparencyOverview,
  SessionResponse,
} from "./types";


const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let onUnauthorizedCallback: (() => void) | null = null;

export function setUnauthorizedHandler(callback: () => void) {
  onUnauthorizedCallback = callback;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (onUnauthorizedCallback) {
      onUnauthorizedCallback();
    }
    throw new ApiError(401, "Session expired or unauthorized. Please log in again.");
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let errorData = null;
    try {
      errorData = await response.json();
      if (errorData.detail) {
        errorDetail = errorData.detail;
      }
    } catch {
      // Ignore JSON parse error on non-JSON response
    }
    throw new ApiError(response.status, errorDetail, errorData);
  }

  return response.json();
}

export const api = {
  // Auth
  async login(username: string, password: string): Promise<TokenResponse> {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const url = `${API_BASE_URL}/api/auth/login`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    if (!res.ok) {
      let detail = "Invalid credentials";
      try {
        const err = await res.json();
        if (err.detail) detail = err.detail;
      } catch {}
      throw new ApiError(res.status, detail);
    }
    return res.json();
  },

  async getMe(token?: string | null): Promise<UserResponse> {
    return request<UserResponse>("/api/auth/me", {}, token);
  },

  // Health
  async getHealth(): Promise<HealthCheckResponse> {
    return request<HealthCheckResponse>("/api/health");
  },

  // Elections
  async getElections(token?: string | null): Promise<ElectionResponse[]> {
    return request<ElectionResponse[]>("/api/elections", {}, token);
  },

  async getElection(
    electionId: string,
    token?: string | null
  ): Promise<ElectionResponse> {
    return request<ElectionResponse>(`/api/elections/${electionId}`, {}, token);
  },

  async updateElectionState(
    electionId: string,
    state: ElectionState,
    token?: string | null
  ): Promise<ElectionResponse> {
    return request<ElectionResponse>(
      `/api/elections/${electionId}/state`,
      {
        method: "PATCH",
        body: JSON.stringify({ state }),
      },
      token
    );
  },

  async addCandidate(
    electionId: string,
    data: CandidateCreate,
    token?: string | null
  ): Promise<CandidateResponse> {
    return request<CandidateResponse>(
      `/api/v1/elections/${electionId}/candidates`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      token
    );
  },

  async deleteCandidate(
    electionId: string,
    candidateId: string,
    token?: string | null
  ): Promise<void> {
    return request<void>(
      `/api/v1/elections/${electionId}/candidates/${candidateId}`,
      {
        method: "DELETE",
      },
      token
    );
  },

  // ============================================================================
  // DEVICES
  // ============================================================================

  async getDevices(
    electionId: string,
    token?: string | null
  ): Promise<DeviceResponse[]> {
    return request<DeviceResponse[]>(
      `/api/elections/${electionId}/devices`,
      {},
      token
    );
  },

  async registerDevice(
    electionId: string,
    data: DeviceRegister,
    token?: string | null
  ): Promise<DeviceResponse> {
    return request<DeviceResponse>(
      `/api/elections/${electionId}/devices`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      token
    );
  },

  async updateDeviceStatus(
    electionId: string,
    deviceId: string,
    status: DeviceStatus,
    token?: string | null
  ): Promise<DeviceResponse> {
    return request<DeviceResponse>(
      `/api/elections/${electionId}/devices/${deviceId}/status`,
      {
        method: "PATCH",
        body: JSON.stringify({ status }),
      },
      token
    );
  },

  // Audit
  async getAuditLog(
    electionId: string,
    token?: string | null
  ): Promise<AuditEntryResponse[]> {
    return request<AuditEntryResponse[]>(
      `/api/elections/${electionId}/audit`,
      {},
      token
    );
  },

  async verifyAuditChain(
    electionId: string,
    token?: string | null
  ): Promise<AuditVerificationResponse> {
    return request<AuditVerificationResponse>(
      `/api/elections/${electionId}/audit/verify`,
      {},
      token
    );
  },

  // Results & Verification
  async getResults(
    electionId: string,
    token?: string | null
  ): Promise<VerificationResponse> {
    return request<VerificationResponse>(
      `/api/elections/${electionId}/results`,
      {},
      token
    );
  },

  async runVerification(
    electionId: string,
    token?: string | null
  ): Promise<VerificationResponse> {
    return request<VerificationResponse>(
      `/api/elections/${electionId}/verify`,
      {
        method: "POST",
      },
      token
    );
  },

  // WebSocket Ticket Handshake (supports election-scoped or global tickets)
  async getWsTicket(
    token?: string | null,
    electionId?: string | null
  ): Promise<WsTicketResponse> {
    return request<WsTicketResponse>(
      "/api/auth/ws-ticket",
      {
        method: "POST",
        body: JSON.stringify({ election_id: electionId || null }),
      },
      token
    );
  },


  // Machine-Verifiable Export
  async exportElection(
    electionId: string,
    token?: string | null
  ): Promise<ElectionExportResponse> {
    return request<ElectionExportResponse>(
      `/api/elections/${electionId}/export`,
      {},
      token
    );
  },

  // Phase 5: Cryptographic Signing
  async getSigningPublicKey(): Promise<PublicKeyInfoResponse> {
    return request<PublicKeyInfoResponse>("/api/signing/public-key");
  },

  async signElectionManifest(
    electionId: string,
    token?: string | null
  ): Promise<SignedManifestResponse> {
    return request<SignedManifestResponse>(
      `/api/elections/${electionId}/sign-manifest`,
      { method: "POST" },
      token
    );
  },

  // Phase 5: Audit Root Anchoring
  async getElectionAnchors(
    electionId: string,
    token?: string | null
  ): Promise<AuditAnchorResponse[]> {
    return request<AuditAnchorResponse[]>(
      `/api/elections/${electionId}/anchors`,
      {},
      token
    );
  },

  async createElectionAnchor(
    electionId: string,
    token?: string | null,
    provider: string = "LOCAL ANCHOR"
  ): Promise<AuditAnchorResponse> {
    return request<AuditAnchorResponse>(
      `/api/elections/${electionId}/anchors`,
      {
        method: "POST",
        body: JSON.stringify({ provider }),
      },
      token
    );
  },

  // Phase 5: Advisory Anomaly Detection
  async getElectionAnomalies(
    electionId: string,
    token?: string | null
  ): Promise<AdvisoryFindingsResponse> {
    return request<AdvisoryFindingsResponse>(
      `/api/elections/${electionId}/anomalies`,
      {},
      token
    );
  },

  // Phase 5: RFID / Identity Abstraction
  async tapRFID(data: RFIDTapRequest): Promise<RFIDTapResponse> {
    return request<RFIDTapResponse>("/api/rfid/tap", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getRFIDDemoCards(): Promise<{ cards: any[]; pseudonymization_algorithm: string; boundary_notice: string }> {
    return request<{ cards: any[]; pseudonymization_algorithm: string; boundary_notice: string }>("/api/rfid/demo-cards");
  },

  // Voters
  async registerVoter(electionId: string, data: { name: string; date_of_birth: string; constituency: string }, token?: string | null): Promise<VoterResponse> {
    return request<VoterResponse>(`/api/elections/${electionId}/voters`, { method: 'POST', body: JSON.stringify(data) }, token);
  },

  async getVoters(electionId: string, token?: string | null): Promise<VoterResponse[]> {
    return request<VoterResponse[]>(`/api/elections/${electionId}/voters`, {}, token);
  },

  async checkEligibility(electionId: string, data: { name: string; date_of_birth: string; constituency: string }): Promise<EligibilityCheckResponse> {
    return request<EligibilityCheckResponse>(`/api/elections/${electionId}/eligibility`, { method: 'POST', body: JSON.stringify(data) });
  },

  async lookupVoter(electionId: string, voterIdNumber: string): Promise<VoterResponse> {
    return request<VoterResponse>(`/api/elections/${electionId}/voter-lookup?voter_id_number=${encodeURIComponent(voterIdNumber)}`);
  },

  // Polling Stations
  async getPollingStations(electionId: string, token?: string | null): Promise<PollingStationResponse[]> {
    return request<PollingStationResponse[]>(`/api/elections/${electionId}/polling-stations`, {}, token);
  },

  async createPollingStation(electionId: string, data: any, token?: string | null): Promise<PollingStationResponse> {
    return request<PollingStationResponse>(`/api/elections/${electionId}/polling-stations`, { method: 'POST', body: JSON.stringify(data) }, token);
  },

  // Complaints
  async submitComplaint(data: { election_id?: string; category: string; description: string; complainant_name: string; complainant_contact?: string }): Promise<ComplaintResponse> {
    return request<ComplaintResponse>('/api/complaints', { method: 'POST', body: JSON.stringify(data) });
  },

  async getComplaints(token?: string | null): Promise<ComplaintResponse[]> {
    return request<ComplaintResponse[]>('/api/complaints', {}, token);
  },

  async trackComplaint(referenceNumber: string): Promise<ComplaintResponse> {
    return request<ComplaintResponse>(`/api/complaints/track/${encodeURIComponent(referenceNumber)}`);
  },

  async updateComplaintStatus(complaintId: string, data: { status: string; assigned_officer?: string; resolution_notes?: string }, token?: string | null): Promise<ComplaintResponse> {
    return request<ComplaintResponse>(`/api/complaints/${complaintId}/status`, { method: 'PATCH', body: JSON.stringify(data) }, token);
  },

  // Simulation
  async runSimulation(data: { preset: string; election_name?: string }, token?: string | null): Promise<SimulationResponse> {
    return request<SimulationResponse>('/api/simulation/run', { method: 'POST', body: JSON.stringify(data) }, token);
  },

  async getSimulationPresets(): Promise<any> {
    return request<any>('/api/simulation/presets');
  },

  // Transparency (public, no auth)
  async getTransparencyElections(): Promise<TransparencyOverview[]> {
    return request<TransparencyOverview[]>('/api/transparency/elections');
  },

  async getTransparencyOverview(electionId: string): Promise<TransparencyOverview> {
    return request<TransparencyOverview>(`/api/transparency/elections/${electionId}`);
  },

  async getTransparencyCandidates(electionId: string): Promise<CandidateResponse[]> {
    return request<CandidateResponse[]>(`/api/transparency/elections/${electionId}/candidates`);
  },

  async getTransparencyResults(electionId: string): Promise<any> {
    return request<any>(`/api/transparency/elections/${electionId}/results`);
  },

  // Voting session (for EVM digital twin)
  async authorizeSession(electionId: string, data: { voter_credential: string; device_id: string }, token?: string | null): Promise<SessionResponse> {
    return request<SessionResponse>(`/api/elections/${electionId}/sessions`, { method: 'POST', body: JSON.stringify(data) }, token);
  },

  async castVote(data: { session_token: string; candidate_id: string; device_id: string; sequence_number: number }): Promise<any> {
    return request<any>('/api/votes', { method: 'POST', body: JSON.stringify(data) });
  },

  async getSessions(electionId: string, token?: string | null): Promise<SessionResponse[]> {
    return request<SessionResponse[]>(`/api/elections/${electionId}/sessions`, {}, token);
  },
};


/**
 * Phase 2 Continuity Helper: Detects whether an event or session is DEMO-MODE synthetic.
 */
export function isDemoMode(record: {
  event_data?: string | null;
  voter_credential?: string | null;
  actor?: string | null;
}): boolean {
  if (record.voter_credential && record.voter_credential.startsWith("VOTER-SERIAL-")) {
    return true;
  }
  if (record.event_data) {
    if (
      record.event_data.includes("VOTER-SERIAL-") ||
      record.event_data.includes("DEMO-MODE") ||
      record.event_data.includes("simulated_session_token")
    ) {
      return true;
    }
  }
  return false;
}
