import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import { loadConfig } from "./config.js";
import { FIXTURE_REQUEST, withFlag } from "./fixtures.js";
import { checkNeutrality } from "./guard.js";
import { buildApp } from "./index.js";
import { mockExplain } from "./mock.js";
import { DETECTORS, ExplainRequestSchema } from "./types.js";

// The SDK Agent is replaced everywhere: no network, no real model.
vi.mock("@cline/sdk", async (importOriginal) => {
  const original = await importOriginal<typeof import("@cline/sdk")>();
  class FakeAgent {
    run = vi.fn(async () => ({ outputText: "{}", status: "completed" }));
    abort = vi.fn();
  }
  return { ...original, Agent: FakeAgent };
});

const MOCK_CONFIG = loadConfig({ MOCK_AGENT: "true" });

describe("POST /explain (mock mode)", () => {
  it("returns the contract shape", async () => {
    const app = await buildApp(MOCK_CONFIG);
    const res = await app.inject({ method: "POST", url: "/explain", payload: FIXTURE_REQUEST });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(Object.keys(body).sort()).toEqual(["explanation", "neutrality", "recommended_checks", "source"]);
    expect(Object.keys(body.explanation).sort()).toEqual(["en", "hi"]);
    expect(body.recommended_checks.length).toBeGreaterThanOrEqual(2);
    expect(body.neutrality).toEqual({ passed: true, method: "mock", violations: [] });
    expect(body.source).toBe("agent");
    expect(body.explanation.en).toContain("22.4%");
    expect(body.explanation.en).toContain("4.8%");
    await app.close();
  });

  it("uses the same shape and numbers as the contract fixture", () => {
    const fixture = JSON.parse(
      readFileSync(new URL("../../contracts/fixtures/explain_response.json", import.meta.url), "utf8"),
    );
    expect(Object.keys(fixture).sort()).toEqual(["explanation", "neutrality", "recommended_checks", "source"]);
    expect(checkNeutrality(fixture, FIXTURE_REQUEST).passed).toBe(true);
  });

  it("gives guard-passing text for every detector", () => {
    const cases = [
      FIXTURE_REQUEST,
      withFlag("REASON_DOMINANCE", "reason_share", 0.82, 0.4),
      withFlag("GENDER_SKEW", "f_removed_share", 0.71, 0.5),
      withFlag("AGE_SKEW", "dead_under_40", 9, 1),
      withFlag("AGE_SKEW", "young_removed_share", 0.34, 0.12),
      withFlag("HOUSE_CLUSTER", "max_house_additions", 14, 3),
      withFlag("HOUSE_CLUSTER", "max_house_voters", 22, 6),
      withFlag("DUPLICATE_ENTRY", "duplicate_pairs", 12, 2),
      withFlag("DATA_QUALITY", "dq_count", 31, 4),
    ];
    for (const payload of cases) {
      const content = mockExplain(payload);
      expect(checkNeutrality(content, payload), payload.flag.metric.name).toEqual({ passed: true, violations: [] });
    }
    expect(new Set(cases.map((c) => c.flag.detector))).toEqual(new Set(DETECTORS));
  });

  it("is deterministic", () => {
    expect(mockExplain(FIXTURE_REQUEST)).toEqual(mockExplain(FIXTURE_REQUEST));
  });
});

describe("request validation", () => {
  it("rejects malformed requests at the schema", () => {
    const bad = [
      {},
      { ...FIXTURE_REQUEST, audit_id: "" },
      { ...FIXTURE_REQUEST, flag: { ...FIXTURE_REQUEST.flag, detector: "NOT_A_DETECTOR" } },
      { ...FIXTURE_REQUEST, flag: { ...FIXTURE_REQUEST.flag, metric: { name: "x", value: "high", baseline: 1 } } },
      { ...FIXTURE_REQUEST, baseline: { deletion_rate: 0.1 } },
      { ...FIXTURE_REQUEST, booth: { part_no: 17 } },
    ];
    for (const body of bad) {
      expect(ExplainRequestSchema.safeParse(body).success).toBe(false);
    }
    expect(ExplainRequestSchema.safeParse(FIXTURE_REQUEST).success).toBe(true);
  });

  it("answers 422 VALIDATION_ERROR over HTTP", async () => {
    const app = await buildApp(MOCK_CONFIG);
    const res = await app.inject({ method: "POST", url: "/explain", payload: { audit_id: "aud_001" } });
    expect(res.statusCode).toBe(422);
    expect(res.json().error.code).toBe("VALIDATION_ERROR");
    await app.close();
  });
});
