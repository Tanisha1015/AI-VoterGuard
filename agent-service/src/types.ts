import { z } from "zod";

/** Request/response shapes for POST /explain (contracts/CONTRACT.md section 6.4). */

export const DETECTORS = [
  "DELETION_RATE",
  "REASON_DOMINANCE",
  "GENDER_SKEW",
  "AGE_SKEW",
  "HOUSE_CLUSTER",
  "DUPLICATE_ENTRY",
  "DATA_QUALITY",
] as const;

export const SEVERITIES = ["LOW", "MEDIUM", "HIGH"] as const;

const NumberMap = z.record(z.string(), z.number());

/** BoothSummary from the contract. Extra keys (for example `flags`) are tolerated and ignored. */
export const BoothSchema = z.looseObject({
  part_no: z.number().int(),
  draft_count: z.number(),
  final_count: z.number(),
  removed: z.number(),
  added: z.number(),
  deletion_rate: z.number(),
  reason_mix: NumberMap,
  female_removed_share: z.number(),
  risk_score: z.number(),
  flagged: z.boolean(),
  flag_count: z.number(),
  gender_removed: NumberMap.optional(),
  age_band_removed_share: NumberMap.optional(),
});

export const ExplainRequestSchema = z.object({
  audit_id: z.string().min(1),
  booth: BoothSchema,
  flag: z.object({
    detector: z.enum(DETECTORS),
    severity: z.enum(SEVERITIES),
    metric: z.object({
      name: z.string().min(1),
      value: z.number(),
      baseline: z.number(),
    }),
  }),
  baseline: z.object({
    deletion_rate: z.number(),
    deletion_rate_mad: z.number(),
  }),
});

export type ExplainRequest = z.infer<typeof ExplainRequestSchema>;

export const BilingualSchema = z.object({
  en: z.string().trim().min(1),
  hi: z.string().trim().min(1),
});

/** What the explainer (and reviewer) must output: text only, no numbers of their own. */
export const ExplainContentSchema = z.object({
  explanation: BilingualSchema,
  recommended_checks: z.array(BilingualSchema).min(2).max(3),
});

export type ExplainContent = z.infer<typeof ExplainContentSchema>;

export interface ExplainResponse extends ExplainContent {
  neutrality: { passed: boolean; method: string; violations: string[] };
  source: "agent";
}

/** The minimal surface of the SDK `Agent` that this service uses (also easy to fake in tests). */
export interface RunnableAgent {
  run(input: string): Promise<{ outputText: string; status: string; error?: Error }>;
  abort(reason?: unknown): void;
}

/** The text failed the neutrality guard after the allowed rewrite attempts (HTTP 422). */
export class NeutralityFailedError extends Error {
  constructor(readonly violations: string[]) {
    super("The generated text did not pass the neutrality guard after the allowed rewrites.");
    this.name = "NeutralityFailedError";
  }
}

/** The agent could not run, failed, or timed out (HTTP 503). */
export class AgentUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AgentUnavailableError";
  }
}
