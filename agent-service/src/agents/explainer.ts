import { Agent } from "@cline/sdk";
import type { AgentConfig } from "../config.js";
import { createRequestTools } from "../tools.js";
import type { ExplainRequest, RunnableAgent } from "../types.js";

/** The explainer agent: phrases one flag in English and Hindi using only tool-provided facts. */

export const EXPLAINER_SYSTEM_PROMPT = `You write short, neutral, bilingual explanations of unusual patterns found in a synthetic electoral-roll audit. A human reviewer will verify every flag. You never decide anything.

Process: call get_flag_metric, get_booth_stats and get_baseline first, then write the answer.

Rules:
- Write 2-3 sentences in English and the same meaning in natural Hindi (Devanagari) describing the unusual pattern.
- Use ONLY facts and numbers returned by the tools. Never add, round differently, or change numbers. Quote percentages from the *_percent fields so they match the data. Do not do your own arithmetic; use ratio_to_baseline and the difference fields when you need a comparison.
- Keep a neutral tone. Never say or imply fraud, illegality, rigging, ineligibility or wrongdoing. Never speculate about causes involving any community, religion, caste or nationality. Only gender and age bands may be discussed, and only if the tools return them.
- Use phrases like "unusual", "worth verifying", "consistent with", "recommend a field check".
- Give 2-3 recommended checks that are practical field-verification steps, for example sample re-verification of households, review of Booth Level Officer visit records, or cross-checking against the supporting-document references. Each check has an English and a Hindi version. Checks need no numbers.
- Output ONLY a JSON object with exactly this shape and nothing else (no markdown fences, no commentary):
{"explanation":{"en":"...","hi":"..."},"recommended_checks":[{"en":"...","hi":"..."}]}`;

export const EXPLAINER_PROMPT = "Explain the flagged pattern for this request. Use the tools, then output only the JSON object.";

/** Create an explainer Agent whose tools read from this request's payload. */
export function createExplainerAgent(config: AgentConfig, payload: ExplainRequest): RunnableAgent {
  return new Agent({
    providerId: config.providerId,
    modelId: config.modelId,
    apiKey: config.apiKey,
    systemPrompt: EXPLAINER_SYSTEM_PROMPT,
    tools: createRequestTools(payload),
    maxIterations: 6,
  });
}
