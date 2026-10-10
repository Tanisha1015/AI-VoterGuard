/** Pure helpers for the booth table: filtering by flag attributes and sorting. */
import type { BoothSummary, Detector, Flag, Severity } from "../api/types";

export type SortKey = "part_no" | "removed" | "deletion_rate" | "risk_score" | "flag_count";
export type SortDir = "asc" | "desc";

export const SORT_COLUMNS: SortKey[] = ["part_no", "removed", "deletion_rate", "risk_score", "flag_count"];
export const SEVERITIES: Severity[] = ["HIGH", "MEDIUM", "LOW"];
export const DETECTORS: Detector[] = [
  "DELETION_RATE",
  "REASON_DOMINANCE",
  "GENDER_SKEW",
  "AGE_SKEW",
  "HOUSE_CLUSTER",
  "DUPLICATE_ENTRY",
  "DATA_QUALITY",
];

/** Keep booths having at least one flag matching both filters ("" means any). */
export function filterBooths(
  booths: BoothSummary[],
  flags: Flag[],
  severity: Severity | "",
  detector: Detector | "",
): BoothSummary[] {
  if (!severity && !detector) return booths;
  const parts = new Set(
    flags
      .filter((f) => (!severity || f.severity === severity) && (!detector || f.detector === detector))
      .map((f) => f.part_no),
  );
  return booths.filter((b) => parts.has(b.part_no));
}

/** Sort by a numeric column; ties broken by part number. Does not mutate input. */
export function sortBooths(booths: BoothSummary[], key: SortKey, dir: SortDir): BoothSummary[] {
  const factor = dir === "asc" ? 1 : -1;
  return [...booths].sort((a, b) => (a[key] - b[key]) * factor || a.part_no - b.part_no);
}
