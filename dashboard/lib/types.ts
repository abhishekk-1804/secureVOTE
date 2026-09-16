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
