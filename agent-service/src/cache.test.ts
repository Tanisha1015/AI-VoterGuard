import { describe, expect, it, vi } from "vitest";
import { canonicalJson, LruCache, requestKey, runAgentWithTimeout, Semaphore } from "./cache.js";
import { AgentUnavailableError, type RunnableAgent } from "./types.js";

describe("requestKey", () => {
  it("ignores key order and is a sha256 hex digest", () => {
    expect(requestKey({ a: 1, b: { c: 2, d: 3 } })).toBe(requestKey({ b: { d: 3, c: 2 }, a: 1 }));
    expect(requestKey({ a: 1 })).toMatch(/^[0-9a-f]{64}$/);
    expect(requestKey({ a: 1 })).not.toBe(requestKey({ a: 2 }));
    expect(canonicalJson({ b: [1, { z: 1, y: 2 }], a: undefined })).toBe('{"b":[1,{"y":2,"z":1}]}');
  });
});

describe("LruCache", () => {
  it("evicts the least recently used entry", () => {
    const cache = new LruCache<number>(2);
    cache.set("a", 1);
    cache.set("b", 2);
    cache.get("a");
    cache.set("c", 3);
    expect(cache.get("b")).toBeUndefined();
    expect(cache.get("a")).toBe(1);
    expect(cache.get("c")).toBe(3);
    expect(cache.size).toBe(2);
  });
});

describe("Semaphore", () => {
  it("never runs more than the limit at once", async () => {
    const semaphore = new Semaphore(3);
    let active = 0;
    let peak = 0;
    const task = async (): Promise<void> => {
      active += 1;
      peak = Math.max(peak, active);
      await new Promise((resolve) => setTimeout(resolve, 5));
      active -= 1;
    };
    await Promise.all(Array.from({ length: 10 }, () => semaphore.run(task)));
    expect(peak).toBe(3);
  });
});

describe("runAgentWithTimeout", () => {
  it("aborts and reports AGENT_UNAVAILABLE on timeout", async () => {
    vi.useFakeTimers();
    const abort = vi.fn();
    const agent: RunnableAgent = { run: () => new Promise(() => undefined), abort };
    const result = runAgentWithTimeout(agent, "go", 20_000);
    const assertion = expect(result).rejects.toBeInstanceOf(AgentUnavailableError);
    await vi.advanceTimersByTimeAsync(20_000);
    await assertion;
    expect(abort).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("rejects a run that did not complete", async () => {
    const agent: RunnableAgent = { run: async () => ({ outputText: "x", status: "failed" }), abort: () => undefined };
    await expect(runAgentWithTimeout(agent, "go", 1000)).rejects.toBeInstanceOf(AgentUnavailableError);
  });
});
