import type { ExplainRequest } from "./types.js";

/**
 * Facts derived deterministically from the request payload. The agent tools return exactly these
 * values, the mock text uses them, and the number guard accepts exactly these numbers.
 */

type Booth = ExplainRequest["booth"];

/** Round to one decimal place. */
export function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

/** 0.224 -> "22.4%". */
export function pct(fraction: number): string {
  return `${(fraction * 100).toFixed(1)}%`;
}

/** 4 -> "4", 4.54 -> "4.5" (counts and medians). */
export function num(value: number): string {
  return String(Number(value.toFixed(1)));
}

/** True when the metric is a share or rate between 0 and 1 (shown as a percentage). */
export function isFractionMetric(name: string, value: number, baseline: number): boolean {
  return /(_rate|_share)$/.test(name) && value >= 0 && value <= 1 && baseline >= 0 && baseline <= 1;
}

/** value / baseline rounded to one decimal, or null when the baseline is not positive. */
export function ratioToBaseline(value: number, baseline: number): number | null {
  return baseline > 0 ? round1(value / baseline) : null;
}

function toPercent(shares: Record<string, number>): Record<string, number> {
  return Object.fromEntries(Object.entries(shares).map(([key, share]) => [key, round1(share * 100)]));
}

/** Booth statistics (no nested flags or text), with percentage forms of every fraction. */
export function boothFacts(booth: Booth): Record<string, unknown> {
  const facts: Record<string, unknown> = {
    part_no: booth.part_no,
    draft_count: booth.draft_count,
    final_count: booth.final_count,
    removed: booth.removed,
    added: booth.added,
    deletion_rate: booth.deletion_rate,
    deletion_rate_percent: round1(booth.deletion_rate * 100),
    reason_mix: booth.reason_mix,
    reason_mix_percent: toPercent(booth.reason_mix),
    female_removed_share: booth.female_removed_share,
    female_removed_share_percent: round1(booth.female_removed_share * 100),
    risk_score: booth.risk_score,
    flagged: booth.flagged,
    flag_count: booth.flag_count,
  };
  if (booth.gender_removed) {
    facts.gender_removed = booth.gender_removed;
  }
  if (booth.age_band_removed_share) {
    facts.age_band_removed_share = booth.age_band_removed_share;
    facts.age_band_removed_share_percent = toPercent(booth.age_band_removed_share);
  }
  return facts;
}

/** Constituency baseline values, with percentage forms. */
export function baselineFacts(baseline: ExplainRequest["baseline"]): Record<string, unknown> {
  return {
    deletion_rate: baseline.deletion_rate,
    deletion_rate_percent: round1(baseline.deletion_rate * 100),
    deletion_rate_mad: baseline.deletion_rate_mad,
    deletion_rate_mad_percent: round1(baseline.deletion_rate_mad * 100),
  };
}

/** The flagged metric, its baseline, and the derived comparison figures. */
export function flagFacts(flag: ExplainRequest["flag"]): Record<string, unknown> {
  const { name, value, baseline } = flag.metric;
  const fraction = isFractionMetric(name, value, baseline);
  const facts: Record<string, unknown> = {
    detector: flag.detector,
    severity: flag.severity,
    metric_name: name,
    unit: fraction ? "fraction (share of 1.0; use the *_percent values in text)" : "count",
    value,
    baseline,
  };
  if (fraction) {
    facts.value_percent = round1(value * 100);
    facts.baseline_percent = round1(baseline * 100);
    facts.difference_percentage_points = round1((value - baseline) * 100);
  } else {
    facts.difference = round1(value - baseline);
  }
  const ratio = ratioToBaseline(value, baseline);
  if (ratio !== null) {
    facts.ratio_to_baseline = ratio;
  }
  return facts;
}
