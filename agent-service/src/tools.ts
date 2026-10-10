import { createTool } from "@cline/sdk";
import { z } from "zod";
import { baselineFacts, boothFacts, flagFacts } from "./facts.js";
import type { ExplainRequest } from "./types.js";

/**
 * Custom tools for one /explain request. They only return values from the request payload held in
 * the closure: no network calls and no call to the core API.
 */

const NoInput = z.object({});

/** The three tools the explainer (and reviewer) may call. */
export function createRequestTools(payload: ExplainRequest) {
  const getBoothStats = createTool({
    name: "get_booth_stats",
    description:
      "Returns the statistics of the flagged booth: counts, deletion rate, reason mix, " +
      "female removed share, risk score and (when present) gender and age-band breakdowns. " +
      "Each fraction also has a *_percent value to quote in text.",
    inputSchema: NoInput,
    async execute() {
      return boothFacts(payload.booth);
    },
  });

  const getBaseline = createTool({
    name: "get_baseline",
    description:
      "Returns the constituency baseline: median deletion rate and its median absolute deviation, " +
      "with percent forms.",
    inputSchema: NoInput,
    async execute() {
      return baselineFacts(payload.baseline);
    },
  });

  const getFlagMetric = createTool({
    name: "get_flag_metric",
    description:
      "Returns the flagged metric: detector, severity, metric name, its value, the comparison " +
      "baseline, and the precomputed difference and ratio to quote. Never compute your own numbers.",
    inputSchema: NoInput,
    async execute() {
      return flagFacts(payload.flag);
    },
  });

  return [getBoothStats, getBaseline, getFlagMetric];
}
