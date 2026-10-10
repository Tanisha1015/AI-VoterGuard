import { createHash } from "node:crypto";
import { AgentUnavailableError, type RunnableAgent } from "./types.js";

/** JSON with sorted keys, so equal bodies always serialise identically. */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(",")}]`;
  }
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([k, v]) => `${JSON.stringify(k)}:${canonicalJson(v)}`);
    return `{${entries.join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

/** sha256 (hex) of the canonical request body: the cache key. */
export function requestKey(body: unknown): string {
  return createHash("sha256").update(canonicalJson(body), "utf8").digest("hex");
}

/** Small in-memory LRU cache (Map keeps insertion order; reads re-insert the key). */
export class LruCache<V> {
  private readonly entries = new Map<string, V>();

  constructor(private readonly maxSize: number) {}

  get size(): number {
    return this.entries.size;
  }

  get(key: string): V | undefined {
    const value = this.entries.get(key);
    if (value === undefined) {
      return undefined;
    }
    this.entries.delete(key);
    this.entries.set(key, value);
    return value;
  }

  set(key: string, value: V): void {
    this.entries.delete(key);
    this.entries.set(key, value);
    while (this.entries.size > this.maxSize) {
      const oldest = this.entries.keys().next();
      if (oldest.done) {
        break;
      }
      this.entries.delete(oldest.value);
    }
  }
}

/** Limits how many async tasks run at the same time; the rest wait in FIFO order. */
export class Semaphore {
  private active = 0;
  private readonly waiting: Array<() => void> = [];

  constructor(private readonly limit: number) {}

  async run<T>(task: () => Promise<T>): Promise<T> {
    if (this.active >= this.limit) {
      await new Promise<void>((resolve) => this.waiting.push(resolve));
    }
    this.active += 1;
    try {
      return await task();
    } finally {
      this.active -= 1;
      this.waiting.shift()?.();
    }
  }
}

/**
 * Run one agent prompt with a timeout. On timeout the agent is aborted and
 * AgentUnavailableError is thrown. A run that does not finish normally is also AgentUnavailable.
 */
export async function runAgentWithTimeout(
  agent: RunnableAgent,
  prompt: string,
  timeoutMs: number,
): Promise<string> {
  let timer: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      agent.abort(new Error("agent run timed out"));
      reject(new AgentUnavailableError(`Agent run timed out after ${timeoutMs} ms.`));
    }, timeoutMs);
  });
  try {
    const result = await Promise.race([agent.run(prompt), timeout]);
    if (result.status !== "completed" || result.outputText.trim() === "") {
      throw new AgentUnavailableError(`Agent run ended with status "${result.status}".`);
    }
    return result.outputText;
  } catch (error) {
    if (error instanceof AgentUnavailableError) {
      throw error;
    }
    throw new AgentUnavailableError("Agent run failed.");
  } finally {
    clearTimeout(timer);
  }
}
