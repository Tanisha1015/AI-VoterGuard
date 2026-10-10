import { Agent } from "@cline/sdk";
import type { AgentConfig } from "../config.js";
import { createRequestTools } from "../tools.js";
import type { ExplainContent, ExplainRequest, RunnableAgent } from "../types.js";

/**
 * The reviewer agent: a second, separate Agent instance. (The SDK documents sub-agents only as a
 * ClineCore session feature, `enableSpawnAgent`; the standalone Agent class has none.)
 * It rewrites text to fix ONLY the listed problems and never changes facts.
 */

export const REVIEWER_SYSTEM_PROMPT = `You are a careful editor for neutral, bilingual (English and Hindi) audit text. You receive a JSON object and a list of violations found by an automatic checker.

Rules:
- Fix ONLY the listed problems. Keep everything else, including the structure, as it is.
- Remove or rephrase any blocked word with neutral wording such as "unusual", "worth verifying", "consistent with", "recommend a field check". Never replace it with another loaded word.
- Fix any number the checker flagged by using the exact value from the tools (get_flag_metric, get_booth_stats, get_baseline; use the *_percent fields for percentages), or remove the number. Never invent or change other numbers.
- Do not add new facts, causes or opinions. Do not speculate about any community, religion, caste or nationality.
- Keep the English and Hindi (Devanagari) versions equivalent in meaning.
- Output ONLY the corrected JSON object with exactly this shape (no markdown fences, no commentary):
{"explanation":{"en":"...","hi":"..."},"recommended_checks":[{"en":"...","hi":"..."}]}`;

/** The prompt for one rewrite attempt: the original JSON and the violations to fix. */
export function buildReviewerPrompt(content: ExplainContent, violations: readonly string[]): string {
  return [
    "Original JSON:",
    JSON.stringify(content),
    "",
    "Violations to fix (fix only these):",
    ...violations.map((v) => `- ${v}`),
    "",
    "Output only the corrected JSON object.",
  ].join("\n");
}

/** Create a reviewer Agent with the same payload-backed tools as the explainer. */
export function createReviewerAgent(config: AgentConfig, payload: ExplainRequest): RunnableAgent {
  return new Agent({
    providerId: config.providerId,
    modelId: config.modelId,
    apiKey: config.apiKey,
    systemPrompt: REVIEWER_SYSTEM_PROMPT,
    tools: createRequestTools(payload),
    maxIterations: 6,
  });
}
