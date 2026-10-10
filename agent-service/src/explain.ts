import { createExplainerAgent, EXPLAINER_PROMPT } from "./agents/explainer.js";
import { buildReviewerPrompt, createReviewerAgent } from "./agents/reviewer.js";
import { LruCache, requestKey, runAgentWithTimeout, Semaphore } from "./cache.js";
import type { AgentConfig } from "./config.js";
import { checkNeutrality } from "./guard.js";
import { mockExplain } from "./mock.js";
import {
  AgentUnavailableError,
  ExplainContentSchema,
  NeutralityFailedError,
  type ExplainContent,
  type ExplainRequest,
  type ExplainResponse,
  type RunnableAgent,
} from "./types.js";

/** Orchestration: explainer -> guard -> (reviewer -> guard) x at most 2 -> response. */

export const MAX_REWRITES = 2;
export const AGENT_METHOD = "blocklist+number_check+agent";
export const MOCK_METHOD = "mock";

type AgentFactory = (config: AgentConfig, payload: ExplainRequest) => RunnableAgent;

export interface ExplainDeps {
  createExplainer: AgentFactory;
  createReviewer: AgentFactory;
}

const DEFAULT_DEPS: ExplainDeps = {
  createExplainer: createExplainerAgent,
  createReviewer: createReviewerAgent,
};

/** Pull the first JSON object out of model output (tolerates code fences and stray text). */
export function parseContent(text: string): ExplainContent | undefined {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end <= start) {
    return undefined;
  }
  try {
    const parsed = ExplainContentSchema.safeParse(JSON.parse(text.slice(start, end + 1)));
    return parsed.success ? parsed.data : undefined;
  } catch {
    return undefined;
  }
}

function respond(content: ExplainContent, method: string): ExplainResponse {
  return {
    explanation: content.explanation,
    recommended_checks: content.recommended_checks,
    neutrality: { passed: true, method, violations: [] },
    source: "agent",
  };
}

/** Deterministic mock-mode response; still passes through the guard as a self-check. */
export function explainMock(payload: ExplainRequest): ExplainResponse {
  const content = mockExplain(payload);
  const result = checkNeutrality(content, payload);
  if (!result.passed) {
    throw new NeutralityFailedError(result.violations);
  }
  return respond(content, MOCK_METHOD);
}

async function runForContent(
  agent: RunnableAgent,
  prompt: string,
  timeoutMs: number,
): Promise<ExplainContent | undefined> {
  return parseContent(await runAgentWithTimeout(agent, prompt, timeoutMs));
}

/** The real agent path. Throws AgentUnavailableError or NeutralityFailedError. */
export async function explainWithAgents(
  payload: ExplainRequest,
  config: AgentConfig,
  deps: ExplainDeps = DEFAULT_DEPS,
): Promise<ExplainResponse> {
  let content = await runForContent(
    deps.createExplainer(config, payload),
    EXPLAINER_PROMPT,
    config.runTimeoutMs,
  );
  if (content === undefined) {
    throw new AgentUnavailableError("The explainer did not return the required JSON.");
  }
  let result = checkNeutrality(content, payload);

  for (let attempt = 0; attempt < MAX_REWRITES && !result.passed; attempt += 1) {
    const rewritten = await runForContent(
      deps.createReviewer(config, payload),
      buildReviewerPrompt(content, result.violations),
      config.runTimeoutMs,
    );
    if (rewritten === undefined) {
      continue; // unusable rewrite: keep the previous text and use up the attempt
    }
    content = rewritten;
    result = checkNeutrality(content, payload);
  }
  if (!result.passed) {
    throw new NeutralityFailedError(result.violations);
  }
  return respond(content, AGENT_METHOD);
}

/** Handles /explain: mock mode, cache, in-flight de-duplication and the concurrency limit. */
export class ExplainService {
  private readonly cache: LruCache<ExplainResponse>;
  private readonly semaphore: Semaphore;
  private readonly inFlight = new Map<string, Promise<ExplainResponse>>();

  constructor(
    readonly config: AgentConfig,
    private readonly deps: ExplainDeps = DEFAULT_DEPS,
  ) {
    this.cache = new LruCache(config.cacheSize);
    this.semaphore = new Semaphore(config.concurrency);
  }

  async explain(payload: ExplainRequest): Promise<ExplainResponse> {
    if (this.config.mock) {
      return explainMock(payload);
    }
    const key = requestKey(payload);
    const cached = this.cache.get(key);
    if (cached !== undefined) {
      return cached;
    }
    const pending = this.inFlight.get(key);
    if (pending !== undefined) {
      return pending;
    }
    const task = this.semaphore
      .run(() => explainWithAgents(payload, this.config, this.deps))
      .then((response) => {
        this.cache.set(key, response);
        return response;
      })
      .finally(() => this.inFlight.delete(key));
    this.inFlight.set(key, task);
    return task;
  }
}
