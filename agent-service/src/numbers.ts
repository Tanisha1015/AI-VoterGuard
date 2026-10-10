import type { ExplainRequest } from "./types.js";

/** Number extraction and the set of numbers the request payload supports. */

const AGE_BAND_LABELS = /\b(?:18-25|26-35|36-45|46-60|61-80)\b|\b80\+/g;
const PERCENT_MARKER = "(?:%|percent\\b|per\\s*cent\\b|प्रतिशत|फीसदी|फीसद)";
const NUMBER_PATTERN = new RegExp(
  `(\\d{1,3}(?:,\\d{3})+(?:\\.\\d+)?|\\d+(?:\\.\\d+)?)(\\s*${PERCENT_MARKER})?`,
  "giu",
);

/** Remove nukta marks so spelling variants compare equal. */
export function stripNukta(text: string): string {
  return text.normalize("NFD").replace(/\u093C/g, "");
}

/** Convert Devanagari digits to ASCII digits. */
function asciiDigits(text: string): string {
  return text.replace(/[\u0966-\u096F]/g, (d) => String(d.charCodeAt(0) - 0x0966));
}

export interface ExtractedNumber {
  /** The number as written, for example "22.4%". */
  raw: string;
  value: number;
  decimals: number;
  isPercent: boolean;
}

/** Every number in a text, with its decimal places and whether it is marked as a percentage. */
export function extractNumbers(text: string): ExtractedNumber[] {
  const cleaned = stripNukta(asciiDigits(text)).replace(AGE_BAND_LABELS, " ");
  const numbers: ExtractedNumber[] = [];
  for (const match of cleaned.matchAll(NUMBER_PATTERN)) {
    const literal = (match[1] ?? "").replace(/,/g, "");
    const decimals = literal.includes(".") ? (literal.split(".")[1] ?? "").length : 0;
    numbers.push({
      raw: match[0].trim(),
      value: Number(literal),
      decimals,
      isPercent: match[2] !== undefined,
    });
  }
  return numbers;
}

export interface AllowedNumbers {
  /** Values that may appear as plain numbers (counts, fractions, ratios, percentages). */
  plain: number[];
  /** Values that may appear next to a percent sign. */
  percent: number[];
}

function collectNumbers(value: unknown, into: number[]): void {
  if (typeof value === "number" && Number.isFinite(value)) {
    into.push(value);
  } else if (Array.isArray(value)) {
    value.forEach((item) => collectNumbers(item, into));
  } else if (value !== null && typeof value === "object") {
    Object.values(value as Record<string, unknown>).forEach((item) => collectNumbers(item, into));
  }
}

/** Every number the text may legitimately contain, derived only from the request payload. */
export function allowedNumbers(payload: ExplainRequest): AllowedNumbers {
  const raw: number[] = [];
  collectNumbers([payload.booth, payload.flag.metric, payload.baseline], raw);

  const plain = [...raw];
  const percent = raw.filter((v) => v >= 0 && v <= 1).map((v) => v * 100);

  const { value, baseline } = payload.flag.metric;
  if (baseline > 0) {
    plain.push(value / baseline);
  }
  if (payload.baseline.deletion_rate > 0) {
    plain.push(payload.booth.deletion_rate / payload.baseline.deletion_rate);
  }
  plain.push(value - baseline, Math.abs(value - baseline));
  if (payload.flag.metric.name.includes("under_40")) {
    plain.push(40); // the age threshold in the metric name
  }
  if (value >= 0 && value <= 1 && baseline >= 0 && baseline <= 1) {
    percent.push(Math.abs(value - baseline) * 100);
  }
  plain.push(...percent);
  return { plain, percent };
}

function matchesAny(candidate: ExtractedNumber, pool: readonly number[]): boolean {
  const tolerance = 0.5 * 10 ** -candidate.decimals + 1e-9;
  return pool.some((allowed) => Math.abs(allowed - candidate.value) <= tolerance);
}

/** Numbers in one text that are not backed by the payload (returned as written). */
export function findUnsupportedNumbers(text: string, allowed: AllowedNumbers): string[] {
  return extractNumbers(text)
    .filter((n) => !matchesAny(n, n.isPercent ? allowed.percent : allowed.plain))
    .map((n) => n.raw);
}
