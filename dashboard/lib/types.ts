/**
 * SecureVOTE API Contract & TypeScript Interfaces.
 * Derived directly and verified against dashboard/lib/openapi-schema.json.
 */

export type Role = "ADMIN" | "AUDITOR" | "OBSERVER";

export type ElectionState =
  | "CREATED"
  | "CONFIGURED"
  | "LOCKED"
  | "OPEN"
  | "SUSPENDED"
  | "CLOSED"
  | "PUBLISHED";

export type DeviceStatus =
  | "REGISTERED"
  | "ACTIVE"
  | "SUSPENDED"
  | "REVOKED";

export interface UserResponse {
  id: string;
  username: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface CandidateResponse {
  id: string;
  name: string;
  party: string | null;
  symbol: string | null;
  position: number;
}

export interface CandidateCreate {
  name: string;
  party?: string | null;
  symbol?: string | null;
  position: number;
}

export interface ElectionResponse {
  id: string;
  title: string;
  description: string | null;
  state: ElectionState;
  configuration_hash: string | null;
  device_count: number;
  ballot_count: number;
  created_at: string;
  opened_at: string | null;
  closed_at: string | null;
  published_at: string | null;
  candidates: CandidateResponse[];
}

export interface DeviceResponse {
  id: string;
  election_id: string;
  name: string;
  status: DeviceStatus;
  device_hash: string | null;
  last_sequence_number: number;
  total_votes_cast: number;
  registered_at: string;
  activated_at: string | null;
  last_seen_at: string | null;
}

export interface DeviceRegister {
  id: string;
  name: string;
  device_hash?: string | null;
}

export interface DeviceStatusUpdate {
  status: DeviceStatus;
}

export interface AuditEntryResponse {
  id: number;
  election_id: string;
  event_type: string;
  event_data: string | null;
  actor: string | null;
  device_id: string | null;
  sequence_number: number;
  timestamp: string;
  previous_hash: string | null;
  entry_hash: string;
}

export interface AuditVerificationResponse {
  election_id: string;
  total_entries: number;
  is_intact: boolean;
  first_broken_sequence: number | null;
  details: string;
}

export interface ReconciliationResult {
  total_ballots: number;
  sum_candidate_totals: number;
  sum_device_totals: number;
  is_exact_match: boolean;
  status: string;
}

export interface CandidateResult {
  candidate_id: string;
  candidate_name: string;
  party: string | null;
  symbol: string | null;
  vote_count: number;
  percentage: number;
}

export interface DeviceResult {
  device_id: string;
  device_name: string;
  ballot_count: number;
}

export interface ResultManifestResponse {
  id: string;
  election_id: string;
  total_ballots: number;
  candidate_totals: string; // JSON string
  device_totals: string;    // JSON string
  reconciliation_status: string;
  audit_chain_status: string;
  configuration_hash: string;
  manifest_hash: string;
  digital_signature: string | null;
  generated_at: string;
  verified_at: string | null;
  verified_by: string | null;
  candidate_results: CandidateResult[];
  device_results: DeviceResult[];
  reconciliation: ReconciliationResult;
}

export interface VerificationResponse {
  election_id: string;
  config_hash_valid: boolean;
  audit_chain_intact: boolean;
  reconciliation_passed: boolean;
  tally_independently_verified: boolean;
  overall_status: string;
  manifest: ResultManifestResponse | null;
  details: string[];
}

export interface SessionResponse {
  id: string;
  election_id: string;
  device_id: string;
  session_token: string;
  voter_credential: string;
  status: string;
  authorized_at: string;
  voted_at: string | null;
}

export interface HealthCheckResponse {
  status: string;
  app: string;
  version: string;
}

export interface WsTicketResponse {
  ticket: string;
  expires_in: number;
  election_id?: string | null;
}


export interface BallotExportItem {
  id: string;
  session_id: string;
  device_id: string;
  candidate_id: string;
  sequence_number: number;
  ballot_hash: string;
  recorded_at: string;
}

export interface AuditExportItem {
  id: number | string;
  sequence_number: number;

  event_type: string;
  event_data: string | null;
  actor: string | null;
  device_id: string | null;
  timestamp: string;
  previous_hash: string | null;
  entry_hash: string;
}

export interface DeviceExportItem {
  id: string;
  name: string;
  status: string;
  last_sequence_number: number;
  total_votes_cast: number;
  registered_at: string;
  activated_at: string | null;
  last_seen_at: string | null;
}

export interface CandidateExportItem {
  id: string;
  name: string;
  party: string | null;
  symbol: string | null;
  position: number;
}

export interface ElectionExportMeta {
  id: string;
  name: string;
  description: string | null;
  state: string;
  configuration_hash: string | null;
  total_ballots: number;
  created_at: string;
  locked_at: string | null;
  opened_at: string | null;
  closed_at: string | null;
  published_at: string | null;
}

export interface ElectionExportResponse {
  export_version: string;
  exported_at: string;
  election: ElectionExportMeta;
  candidates: CandidateExportItem[];
  devices: DeviceExportItem[];
  ballots: BallotExportItem[];
  audit_log: AuditExportItem[];
  manifest: any | null;
  export_hash: string;
}

// ===========================================================================
// Phase 5: Cryptographic Signing, Anchoring, Anomalies & RFID Types
// ===========================================================================

export interface PublicKeyInfoResponse {
  key_id: string;
  algorithm: string;
  public_key_hex: string;
  fingerprint: string;
  status: string;
}

export interface SignedManifestResponse {
  manifest_id: string;
  election_id: string;
  manifest_hash: string;
  digital_signature: {
    algorithm?: string;
    key_id?: string;
    public_key?: string;
    signature?: string;
    fingerprint?: string;
    signed_payload?: Record<string, any>;
  };
  signed_at?: string;
  signed_by?: string;
}

export interface AuditAnchorResponse {
  anchor_id: string;
  election_id: string;
  provider: string;
  root_hash: string;
  anchored_at: string;
  actor?: string | null;
  commitment_receipt: {
    status: string;
    provider?: string;
    timestamp?: string;
    receipt_id?: string;
    [key: string]: any;
  };
}

export interface AdvisoryFinding {
  finding_id: string;
  election_id: string;
  device_id?: string | null;
  rule_id: string;
  category: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  evidence: Record<string, any>;
  timestamp: string;
  advisory_explanation: string;
  requires_human_review: boolean;
}

export interface AdvisoryFindingsResponse {
  election_id: string;
  findings_count: number;
  findings: AdvisoryFinding[];
  status: string;
}

export interface RFIDTapRequest {
  raw_uid: string;
  device_id: string;
  election_id: string;
}

export interface RFIDTapResponse {
  authenticated: boolean;
  pseudonym: string;
  card_status: "VALID" | "INVALID" | "REVOKED" | "REPEATED_USE";
  device_id: string;
  session_id?: string | null;
  notice: string;
}

export interface IndependentVerificationResult {
  valid: boolean;
  checks: {
    export_envelope: boolean;
    configuration: boolean;
    ballot_hashes: boolean;
    ballot_sequence: boolean;
    candidate_totals: boolean;
    device_totals: boolean;
    reconciliation: boolean;
    audit_chain: boolean;
    audit_root: boolean;
    manifest: boolean;
    signature: boolean;
    anchor: boolean;
  };
  failures: string[];
  details: string[];
  summary: {
    election_id: string;
    total_ballots_recounted: number;
    candidates_recounted: number;
    devices_recounted: number;
    audit_entries_recomputed: number;
    audit_root_hash: string;
    reconciliation_drift: number;
  };
}


// Voter types
export interface VoterResponse {
  id: string;
  election_id: string;
  voter_id_number: string;
  name: string;
  date_of_birth: string;
  constituency: string;
  polling_station_id: string | null;
  eligibility_status: string;
  registration_status: string;
  has_voted: boolean;
  registered_at: string;
}

export interface EligibilityCheckResponse {
  status: 'ELIGIBLE' | 'NOT_ELIGIBLE' | 'NEEDS_REVIEW';
  reasons: string[];
  voter_id: string | null;
  notice: string;
}

// Polling Station types
export interface PollingStationResponse {
  id: string;
  election_id: string;
  station_code: string;
  name: string;
  constituency: string;
  location: string;
  assigned_devices: number;
  registered_voters: number;
  votes_cast: number;
  status: string;
  officer_name: string | null;
  created_at: string;
}

// Complaint types
export interface ComplaintResponse {
  id: string;
  election_id: string | null;
  reference_number: string;
  category: string;
  description: string;
  complainant_name: string;
  complainant_contact: string | null;
  status: string;
  assigned_officer: string | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
}

// Simulation types
export interface SimulationResponse {
  election_id: string;
  preset: string;
  ballots_generated: number;
  devices_created: number;
  polling_stations_created: number;
  voters_registered: number;
  candidates_created: number;
  audit_entries: number;
  duration_seconds: number;
  status: string;
}

// Transparency types
export interface TransparencyOverview {
  election_id: string;
  election_name: string;
  state: string;
  total_ballots: number;
  device_count: number;
  polling_station_count: number;
  candidate_count: number;
  registered_voters: number;
  turnout_percentage: number;
  audit_chain_status: string;
  reconciliation_status: string;
  manifest_status: string;
  notice: string;
}
