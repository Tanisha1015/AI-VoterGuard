/** Typed functions for the Core API (Member A, :8000). See CONTRACT.md 6.3. */
import { apiGet, apiPost, apiPut } from "./client";
import type {
  AuditList,
  AuditSummary,
  BoothDetail,
  BoothList,
  CitizenLookupRequest,
  CitizenLookupResponse,
  ExportPayload,
  Flag,
  FlagList,
  FlagQuery,
  ReviewRequest,
} from "./types";

/** Audit used by reviewer pages; configurable via VITE_AUDIT_ID. */
export const DEFAULT_AUDIT_ID = import.meta.env.VITE_AUDIT_ID ?? "aud_001";

const audit = (auditId: string) => `/api/audits/${encodeURIComponent(auditId)}`;

/** GET /api/audits: list of available audits (newest first is up to the server). */
export function getAudits(): Promise<AuditList> {
  return apiGet<AuditList>("core", "/api/audits");
}

export function getSummary(auditId: string = DEFAULT_AUDIT_ID): Promise<AuditSummary> {
  return apiGet<AuditSummary>("core", `${audit(auditId)}/summary`);
}

export function getBooths(auditId: string = DEFAULT_AUDIT_ID): Promise<BoothList> {
  return apiGet<BoothList>("core", `${audit(auditId)}/booths`);
}

export function getBoothDetail(partNo: number, auditId: string = DEFAULT_AUDIT_ID): Promise<BoothDetail> {
  return apiGet<BoothDetail>("core", `${audit(auditId)}/booths/${partNo}`);
}

export function getFlags(query: FlagQuery = {}, auditId: string = DEFAULT_AUDIT_ID): Promise<FlagList> {
  const params = new URLSearchParams();
  if (query.part_no !== undefined) params.set("part_no", String(query.part_no));
  if (query.severity) params.set("severity", query.severity);
  if (query.detector) params.set("detector", query.detector);
  const qs = params.toString();
  return apiGet<FlagList>("core", `${audit(auditId)}/flags${qs ? `?${qs}` : ""}`);
}

export function reviewFlag(flagId: string, body: ReviewRequest, auditId: string = DEFAULT_AUDIT_ID): Promise<Flag> {
  return apiPut<Flag>("core", `${audit(auditId)}/flags/${encodeURIComponent(flagId)}/review`, body);
}

export function getExport(auditId: string = DEFAULT_AUDIT_ID): Promise<ExportPayload> {
  return apiGet<ExportPayload>("core", `${audit(auditId)}/export`);
}

export function citizenLookup(body: CitizenLookupRequest): Promise<CitizenLookupResponse> {
  return apiPost<CitizenLookupResponse>("core", "/api/citizen/lookup", body);
}
