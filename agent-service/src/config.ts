/** Runtime configuration read from environment variables. */
export interface AgentConfig {
  port: number;
  apiKey: string | undefined;
  providerId: string;
  modelId: string;
  /** True when MOCK_AGENT=true or no API key is set: no LLM is ever called. */
  mock: boolean;
  /** Per agent run timeout in milliseconds. */
  runTimeoutMs: number;
  /** Maximum agent runs in flight at once. */
  concurrency: number;
  /** Maximum cached explanations. */
  cacheSize: number;
}

export const DEFAULT_PORT = 8001;
export const DEFAULT_PROVIDER_ID = "anthropic";
export const DEFAULT_MODEL_ID = "claude-sonnet-5-5";
export const DEFAULT_RUN_TIMEOUT_MS = 20_000;
export const DEFAULT_CONCURRENCY = 3;
export const DEFAULT_CACHE_SIZE = 500;

function positiveInt(raw: string | undefined, fallback: number): number {
  const value = Number(raw);
  return Number.isInteger(value) && value > 0 ? value : fallback;
}

/** Build the configuration from an environment object (defaults to process.env). */
export function loadConfig(env: NodeJS.ProcessEnv = process.env): AgentConfig {
  const apiKey = env.ANTHROPIC_API_KEY?.trim() || undefined;
  const forcedMock = env.MOCK_AGENT?.trim().toLowerCase() === "true";
  return {
    port: positiveInt(env.PORT, DEFAULT_PORT),
    apiKey,
    providerId: env.AGENT_PROVIDER_ID?.trim() || DEFAULT_PROVIDER_ID,
    modelId: env.AGENT_MODEL_ID?.trim() || DEFAULT_MODEL_ID,
    mock: forcedMock || apiKey === undefined,
    runTimeoutMs: positiveInt(env.AGENT_RUN_TIMEOUT_MS, DEFAULT_RUN_TIMEOUT_MS),
    concurrency: DEFAULT_CONCURRENCY,
    cacheSize: positiveInt(env.AGENT_CACHE_SIZE, DEFAULT_CACHE_SIZE),
  };
}
