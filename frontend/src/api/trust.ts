/** Typed functions for the Trust service (Member B, :8002). See CONTRACT.md 6.5. */
import { apiGet, apiGetBlob, apiPost, baseUrl } from "./client";
import type {
  ChainStatus,
  CreateReportRequest,
  ReportCreated,
  ReportDetail,
  ReportList,
  VerifyResult,
} from "./types";

export function createReport(body: CreateReportRequest): Promise<ReportCreated> {
  return apiPost<ReportCreated>("trust", "/api/reports", body);
}

/** Absolute URL for a trust-service file path such as "/files/VG-2026-0001.json". */
export function trustFileUrl(path: string): string {
  return `${baseUrl("trust")}${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * Download the recorded report JSON ({VITE_TRUST_URL}/files/{id}.json) as a File,
 * byte-for-byte, ready to be verified.
 */
export async function fetchReportFile(reportId: string): Promise<File> {
  const name = `${reportId}.json`;
  const blob = await apiGetBlob("trust", `/files/${encodeURIComponent(name)}`);
  return new File([blob], name, { type: "application/json" });
}

export function listReports(): Promise<ReportList> {
  return apiGet<ReportList>("trust", "/api/reports");
}

export function getReport(reportId: string): Promise<ReportDetail> {
  return apiGet<ReportDetail>("trust", `/api/reports/${encodeURIComponent(reportId)}`);
}

/** Multipart upload: file is required; report_id is optional (read from the file if absent). */
export function verifyReport(file: File, reportId?: string): Promise<VerifyResult> {
  const form = new FormData();
  form.append("file", file);
  if (reportId) form.append("report_id", reportId);
  return apiPost<VerifyResult>("trust", "/api/reports/verify", form);
}

export function chainStatus(): Promise<ChainStatus> {
  return apiGet<ChainStatus>("trust", "/api/chain/status");
}
