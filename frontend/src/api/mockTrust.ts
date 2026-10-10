/**
 * In-memory stand-in for the trust service's state (mock mode only).
 * Mirrors the real service: ids increase, supersedes is checked, and verify compares content.
 */
import type { ReportCreated, ReportListItem, VerifyResult } from "./types";
import { canonicalJson } from "../lib/canonical";
import exportPayload from "../mocks/export.json";
import reportCreated from "../mocks/report_created.json";
import reportList from "../mocks/report_list.json";
import verifyMatch from "../mocks/verify_match.json";
import verifyMismatch from "../mocks/verify_mismatch.json";

/** Simulated HTTP failure raised by mock handlers. */
export class MockHttpError extends Error {
  readonly status: number;
  readonly code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "MockHttpError";
    this.status = status;
    this.code = code;
  }
}

interface StoredReport extends ReportListItem {
  supersedes: string | null;
  reviewer_name: string;
}

let reports: StoredReport[] = [];

/** Restore the fixture state (used between tests). */
export function resetTrustMock(): void {
  reports = reportList.items.map((item) => ({
    ...item,
    supersedes: reportList.items.find((other) => other.superseded_by === item.report_id)?.report_id ?? null,
    reviewer_name: "R. Sharma",
  }));
}
resetTrustMock();

function find(reportId: string): StoredReport | undefined {
  return reports.find((r) => r.report_id === reportId);
}

/** Synthetic "saved report file" for a mock report (same top-level shape as the real file). */
export function mockReportFileText(reportId: string): string {
  const report = find(reportId);
  if (!report) throw new MockHttpError(404, "FILE_NOT_FOUND", "File not found.");
  return canonicalJson({
    schema_version: "1.0",
    report_id: report.report_id,
    generated_at: report.recorded_at,
    reviewer: { name: report.reviewer_name },
    audit: exportPayload,
    supersedes: report.supersedes,
  });
}

export function listMockReports(): { items: ReportListItem[] } {
  return {
    items: reports.map(({ report_id, recorded_at, report_hash, superseded_by }) => ({
      report_id, recorded_at, report_hash, superseded_by,
    })),
  };
}

function toCreated(report: StoredReport): ReportCreated {
  return {
    ...reportCreated,
    report_id: report.report_id,
    report_hash: report.report_hash,
    recorded_at: report.recorded_at,
    supersedes: report.supersedes,
    files: { json: `/files/${report.report_id}.json`, pdf: `/files/${report.report_id}.pdf` },
  };
}

export function getMockReport(reportId: string): ReportCreated & { superseded_by: string | null } {
  const report = find(reportId);
  if (!report) throw new MockHttpError(404, "REPORT_NOT_FOUND", `Report ${reportId} does not exist.`);
  return { ...toCreated(report), superseded_by: report.superseded_by };
}

/** POST /api/reports in mock mode: next id, supersedes validated like the real service. */
export function createMockReport(body: { reviewer_name?: string; supersedes?: string | null }): ReportCreated {
  const supersedes = body.supersedes ?? null;
  const old = supersedes ? find(supersedes) : undefined;
  if (supersedes && !old) {
    throw new MockHttpError(404, "SUPERSEDED_REPORT_NOT_FOUND", `Report ${supersedes} does not exist.`);
  }
  if (old?.superseded_by) {
    throw new MockHttpError(409, "ALREADY_SUPERSEDED", `Report ${supersedes} was already superseded by ${old.superseded_by}.`);
  }
  const next = Math.max(0, ...reports.map((r) => Number(r.report_id.split("-")[2]) || 0)) + 1;
  const reportId = `VG-${new Date().getUTCFullYear()}-${String(next).padStart(4, "0")}`;
  const hex = Array.from(reportId, (c) => c.charCodeAt(0).toString(16)).join("");
  const stored: StoredReport = {
    report_id: reportId,
    recorded_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    report_hash: `0x${hex.padEnd(64, "0").slice(0, 64)}`,
    superseded_by: null,
    supersedes,
    reviewer_name: body.reviewer_name ?? "",
  };
  if (old) old.superseded_by = reportId;
  reports = [stored, ...reports];
  return toCreated(stored);
}

function reportIdFromText(text: string): string | null {
  try {
    const parsed: unknown = JSON.parse(text);
    const id = parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>).report_id : null;
    return typeof id === "string" && id ? id : null;
  } catch {
    return null;
  }
}

/** POST /api/reports/verify in mock mode: MATCH only if the text equals the mock original. */
export function verifyMock(fileText: string, formReportId: string | null): VerifyResult {
  const reportId = formReportId || reportIdFromText(fileText);
  if (!reportId) throw new MockHttpError(422, "REPORT_ID_REQUIRED", "Could not read report_id from the file.");
  const report = find(reportId);
  if (!report) {
    return { report_id: reportId, status: "NOT_FOUND", computed_hash: verifyMismatch.computed_hash,
      onchain_hash: null, recorded_at: null, submitter: null, superseded_by: null };
  }
  const same = fileText === mockReportFileText(reportId);
  return {
    report_id: reportId,
    status: same ? "MATCH" : "MISMATCH",
    computed_hash: same ? report.report_hash : verifyMismatch.computed_hash,
    onchain_hash: report.report_hash,
    recorded_at: report.recorded_at,
    submitter: verifyMatch.submitter,
    superseded_by: report.superseded_by,
  };
}
