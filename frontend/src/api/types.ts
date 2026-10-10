/**
 * Types mirroring contracts/CONTRACT.md section 6 exactly.
 * Field names are snake_case on purpose: do not rename them.
 */

// ---------- 6.1 Enums ----------
export type Reason = "ABSENT" | "SHIFTED" | "DEAD" | "DUPLICATE";
export type Detector =
  | "DELETION_RATE"
  | "REASON_DOMINANCE"
  | "GENDER_SKEW"
  | "AGE_SKEW"
  | "HOUSE_CLUSTER"
  | "DUPLICATE_ENTRY"
  | "DATA_QUALITY";
export type Severity = "LOW" | "MEDIUM" | "HIGH";
export type ReviewStatus = "PENDING" | "ACCEPTED" | "REJECTED";
export type CitizenStatus = "PRESENT" | "REMOVED" | "ADDED" | "NOT_FOUND" | "AMBIGUOUS";
export type VerifyStatus = "MATCH" | "MISMATCH" | "NOT_FOUND";
export type Gender = "M" | "F" | "O";
export type RelationType = "FATHER" | "HUSBAND" | "MOTHER" | "OTHER";
export type AgeBand = "18-25" | "26-35" | "36-45" | "46-60" | "61-80" | "80+";
export type ExplanationSource = "agent" | "template";
export type Lang = "en" | "hi";

// ---------- 6.1 Conventions ----------
/** Bilingual text: always {"en": "...", "hi": "..."}. */
export interface Bilingual {
  en: string;
  hi: string;
}

/** Error body: {"error": {"code": "SOME_CODE", "message": "Human readable"}}. */
export interface ApiErrorBody {
  error: { code: string; message: string };
}

/** Lowercase 0x + 64 hex characters. */
export type Hash = string;

export interface SnapshotHashes {
  draft: Hash;
  final: Hash;
  asdd: Hash;
}

export type ReasonMix = Record<Reason, number>;

// ---------- 6.3 Core API ----------
export interface HealthResponse {
  status: "ok";
  audit_ready: boolean;
}

export interface CreateAuditResponse {
  audit_id: string;
  status: "READY";
}

export interface AuditListItem {
  audit_id: string;
  ac_name: string;
  created_at: string;
}

export interface AuditList {
  items: AuditListItem[];
}

export interface Totals {
  draft_count: number;
  final_count: number;
  removed: number;
  added: number;
  modified: number;
  booths: number;
  flagged_booths: number;
  flags: number;
  pending_reviews: number;
}

export interface ConstituencyBaseline {
  deletion_rate: number;
  deletion_rate_mad: number;
}

export interface AuditSummary {
  audit_id: string;
  ac_no: number;
  ac_name: string;
  created_at: string;
  snapshot_hashes: SnapshotHashes;
  totals: Totals;
  constituency_baseline: ConstituencyBaseline;
  reason_mix: ReasonMix;
}

export interface BoothSummary {
  part_no: number;
  draft_count: number;
  final_count: number;
  removed: number;
  added: number;
  deletion_rate: number;
  reason_mix: ReasonMix;
  female_removed_share: number;
  risk_score: number;
  flagged: boolean;
  flag_count: number;
}

export interface BoothList {
  items: BoothSummary[];
}

export interface FlagMetric {
  name: string;
  value: number;
  baseline: number;
}

export interface Review {
  status: ReviewStatus;
  note: string | null;
  reviewed_at: string | null;
}

export interface Flag {
  flag_id: string;
  part_no: number;
  detector: Detector;
  severity: Severity;
  metric: FlagMetric;
  explanation: Bilingual;
  recommended_checks: Bilingual[];
  explanation_source: ExplanationSource;
  review: Review;
}

export interface FlagList {
  items: Flag[];
}

export interface FlagQuery {
  part_no?: number;
  severity?: Severity;
  detector?: Detector;
}

export interface BoothDetail extends BoothSummary {
  gender_removed: Record<Gender, number>;
  age_band_removed_share: Record<AgeBand, number>;
  flags: Flag[];
}

export interface ReviewRequest {
  status: ReviewStatus;
  note: string | null;
}

export interface ExportPayload {
  audit_id: string;
  ac_no: number;
  ac_name: string;
  generated_at: string;
  snapshot_hashes: SnapshotHashes;
  summary: {
    totals: Totals;
    constituency_baseline: ConstituencyBaseline;
  };
  flagged_booths: { booth: BoothSummary; flags: Flag[] }[];
  methodology: {
    version: string;
    detectors: Detector[];
    thresholds: Record<string, number>;
  };
  disclaimer: Bilingual;
}

export interface CitizenLookupRequest {
  name: string | null;
  relative_name: string | null;
  part_no: number | null;
  epic_no: string | null;
  lang: Lang;
}

export interface CitizenRecord {
  epic_masked: string;
  part_no: number;
  name_display: string;
  age_band: AgeBand;
}

export interface NextStep {
  title: Bilingual;
  steps: Bilingual[];
  deadline: string;
  disclaimer: Bilingual;
}

export interface CitizenLookupResponse {
  status: CitizenStatus;
  match_confidence: number;
  record: CitizenRecord | null;
  reason: Reason | null;
  next_step: NextStep | null;
  /** Present for AMBIGUOUS ("returns a message and never lists candidates"). */
  message?: Bilingual;
}

// ---------- 6.5 Trust service ----------
export interface CreateReportRequest {
  audit_id: string;
  reviewer_name: string;
  supersedes: string | null;
}

export interface ReportFiles {
  json: string;
  pdf: string;
}

export interface ReportCreated {
  report_id: string;
  report_hash: Hash;
  snapshot_hashes: SnapshotHashes;
  tx_hash: Hash;
  block_number: number;
  recorded_at: string;
  supersedes: string | null;
  files: ReportFiles;
}

export interface ReportDetail extends ReportCreated {
  superseded_by: string | null;
}

export interface ReportListItem {
  report_id: string;
  recorded_at: string;
  report_hash: Hash;
  superseded_by: string | null;
}

export interface ReportList {
  items: ReportListItem[];
}

export interface VerifyResult {
  report_id: string;
  status: VerifyStatus;
  computed_hash: Hash;
  /** null when status is NOT_FOUND (nothing recorded on chain for this id). */
  onchain_hash: Hash | null;
  recorded_at: string | null;
  submitter: string | null;
  superseded_by: string | null;
}

export interface ChainStatus {
  connected: boolean;
  chain_id: number;
  contract_address: string;
  latest_block: number;
}
