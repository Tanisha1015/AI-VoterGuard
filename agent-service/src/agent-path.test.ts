import { describe, expect, it, vi } from "vitest";
import { loadConfig } from "./config.js";
import { ExplainService, parseContent } from "./explain.js";
import { FIXTURE_REQUEST } from "./fixtures.js";
import { buildApp } from "./index.js";
import type { RunnableAgent } from "./types.js";

// The SDK Agent is replaced everywhere: no network, no real model.
vi.mock("@cline/sdk", async (importOriginal) => {
  const original = await importOriginal<typeof import("@cline/sdk")>();
  class FakeAgent {
    run = vi.fn(async () => ({ outputText: "{}", status: "completed" }));
    abort = vi.fn();
  }
  return { ...original, Agent: FakeAgent };
});

const AGENT_CONFIG = loadConfig({ ANTHROPIC_API_KEY: "test-key" });

const GOOD = JSON.stringify({
  explanation: {
    en: "Booth 17 shows a deletion rate of 22.4%, compared with a baseline of 4.8%. This is unusual and worth verifying.",
    hi: "भाग संख्या 17 में नाम हटाने की दर 22.4% है, जबकि आधारभूत औसत 4.8% है। यह असामान्य है और सत्यापन के योग्य है।",
  },
  recommended_checks: [
    { en: "Recommend a field check of a sample of entries.", hi: "प्रविष्टियों के नमूने की क्षेत्रीय जाँच की सिफारिश की जाती है।" },
    { en: "Review Booth Level Officer visit records.", hi: "बूथ स्तर अधिकारी के भ्रमण अभिलेखों की समीक्षा करें।" },
  ],
});
const BAD = GOOD.replace("22.4%", "98%").replace("unusual", "fraud");

/** A fake SDK agent that returns the given outputs in order (the last repeats). */
function fakeAgent(outputs: string[], calls: { n: number } = { n: 0 }): RunnableAgent {
  return {
    run: async () => ({ outputText: outputs[Math.min(calls.n++, outputs.length - 1)] ?? "", status: "completed" }),
    abort: () => undefined,
  };
}

const deps = (explainer: RunnableAgent, reviewer: RunnableAgent) => ({
  createExplainer: () => explainer,
  createReviewer: () => reviewer,
});

describe("agent path", () => {
  it("returns the agent output when the guard passes", async () => {
    const service = new ExplainService(AGENT_CONFIG, deps(fakeAgent([GOOD]), fakeAgent([GOOD])));
    const app = await buildApp(AGENT_CONFIG, service);
    const res = await app.inject({ method: "POST", url: "/explain", payload: FIXTURE_REQUEST });
    expect(res.statusCode).toBe(200);
    expect(res.json().neutrality).toEqual({ passed: true, method: "blocklist+number_check+agent", violations: [] });
    expect(res.json().source).toBe("agent");
    await app.close();
  });

  it("accepts JSON wrapped in a code fence", () => {
    expect(parseContent("```json\n" + GOOD + "\n```")).toBeDefined();
    expect(parseContent("no json here")).toBeUndefined();
  });

  it("uses the reviewer to fix violations", async () => {
    const reviewerCalls = { n: 0 };
    const service = new ExplainService(AGENT_CONFIG, deps(fakeAgent([BAD]), fakeAgent([GOOD], reviewerCalls)));
    const response = await service.explain(FIXTURE_REQUEST);
    expect(reviewerCalls.n).toBe(1);
    expect(response.neutrality.passed).toBe(true);
  });

  it("returns 422 NEUTRALITY_FAILED after 2 failed rewrites", async () => {
    const reviewerCalls = { n: 0 };
    const service = new ExplainService(AGENT_CONFIG, deps(fakeAgent([BAD]), fakeAgent([BAD], reviewerCalls)));
    const app = await buildApp(AGENT_CONFIG, service);
    const res = await app.inject({ method: "POST", url: "/explain", payload: FIXTURE_REQUEST });
    expect(res.statusCode).toBe(422);
    expect(res.json().error.code).toBe("NEUTRALITY_FAILED");
    expect(reviewerCalls.n).toBe(2);
    await app.close();
  });

  it("returns 503 AGENT_UNAVAILABLE when the agent run fails", async () => {
    const failing: RunnableAgent = {
      run: async () => {
        throw new Error("network down");
      },
      abort: () => undefined,
    };
    const service = new ExplainService(AGENT_CONFIG, deps(failing, failing));
    const app = await buildApp(AGENT_CONFIG, service);
    const res = await app.inject({ method: "POST", url: "/explain", payload: FIXTURE_REQUEST });
    expect(res.statusCode).toBe(503);
    expect(res.json().error.code).toBe("AGENT_UNAVAILABLE");
    await app.close();
  });

  it("caches identical requests", async () => {
    const calls = { n: 0 };
    const service = new ExplainService(AGENT_CONFIG, deps(fakeAgent([GOOD], calls), fakeAgent([GOOD])));
    await service.explain(FIXTURE_REQUEST);
    await service.explain(structuredClone(FIXTURE_REQUEST));
    expect(calls.n).toBe(1);
  });
});
