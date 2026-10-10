/** Small, pure formatting helpers shared by reviewer components. */
import type { Lang } from "../api/types";

const LOCALE: Record<Lang, string> = { en: "en-IN", hi: "hi-IN" };

/** Integer with locale grouping, e.g. 48,210. */
export function formatNumber(value: number, lang: Lang): string {
  return new Intl.NumberFormat(LOCALE[lang]).format(value);
}

/** Share (0..1) as a percentage with one decimal, e.g. 0.224 -> "22.4%". */
export function formatPercent(share: number): string {
  return `${(share * 100).toFixed(1)}%`;
}

/** ISO timestamp as a readable local date-time. Falls back to the raw string. */
export function formatDateTime(iso: string, lang: Lang): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(LOCALE[lang], { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(date) + " UTC";
}

/** Shorten a 0x hash for display: 0x1234…abcd. */
export function shortHash(hash: string, head = 6, tail = 4): string {
  if (hash.length <= head + tail + 1) return hash;
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`;
}

/** Sequential single-hue scale (blue) with 5 steps; returns tile classes with readable contrast. */
export function riskShade(score: number): { bg: string; text: string; step: number } {
  const steps = [
    { bg: "bg-blue-50", text: "text-slate-900" },
    { bg: "bg-blue-200", text: "text-slate-900" },
    { bg: "bg-blue-400", text: "text-slate-900" },
    { bg: "bg-blue-600", text: "text-white" },
    { bg: "bg-blue-800", text: "text-white" },
  ] as const;
  const clamped = Math.max(0, Math.min(100, score));
  const step = Math.min(4, Math.floor(clamped / 20));
  const shade = steps[step] ?? steps[0];
  return { ...shade, step };
}

/** Lower and upper score bounds for each scale step (for the legend). */
export const RISK_STEPS: readonly [number, number][] = [
  [0, 19],
  [20, 39],
  [40, 59],
  [60, 79],
  [80, 100],
];
