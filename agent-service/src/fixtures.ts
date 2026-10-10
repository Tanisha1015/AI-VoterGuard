import type { ExplainRequest } from "./types.js";

/** The request from contracts/CONTRACT.md 6.4 (booth 17), shared by the tests. */
export const FIXTURE_REQUEST: ExplainRequest = {
  audit_id: "aud_001",
  booth: {
    part_no: 17,
    draft_count: 812,
    final_count: 640,
    removed: 182,
    added: 10,
    deletion_rate: 0.224,
    reason_mix: { ABSENT: 0.1, SHIFTED: 0.82, DEAD: 0.05, DUPLICATE: 0.03 },
    female_removed_share: 0.71,
    risk_score: 87,
    flagged: true,
    flag_count: 3,
  },
  flag: {
    detector: "DELETION_RATE",
    severity: "HIGH",
    metric: { name: "deletion_rate", value: 0.224, baseline: 0.048 },
  },
  baseline: { deletion_rate: 0.048, deletion_rate_mad: 0.012 },
};

/** Build a request for another detector by overriding the flag. */
export function withFlag(
  detector: ExplainRequest["flag"]["detector"],
  name: string,
  value: number,
  baseline: number,
): ExplainRequest {
  return { ...FIXTURE_REQUEST, flag: { detector, severity: "MEDIUM", metric: { name, value, baseline } } };
}
