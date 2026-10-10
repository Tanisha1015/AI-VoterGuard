import { describe, expect, it } from "vitest";
import { loadConfig } from "./config.js";
import { FIXTURE_REQUEST } from "./fixtures.js";
import { createRequestTools } from "./tools.js";

describe("request tools", () => {
  const tools = createRequestTools(FIXTURE_REQUEST);
  const context = { agentId: "a", iteration: 1 };
  const call = async (name: string): Promise<Record<string, unknown>> => {
    const tool = tools.find((t) => t.name === name);
    expect(tool, name).toBeDefined();
    return (await tool!.execute({}, context)) as Record<string, unknown>;
  };

  it("exposes the three tools", () => {
    expect(tools.map((t) => t.name)).toEqual(["get_booth_stats", "get_baseline", "get_flag_metric"]);
  });

  it("returns payload data with percent forms", async () => {
    const booth = await call("get_booth_stats");
    expect(booth.removed).toBe(182);
    expect(booth.deletion_rate_percent).toBe(22.4);
    const baseline = await call("get_baseline");
    expect(baseline.deletion_rate_percent).toBe(4.8);
    const metric = await call("get_flag_metric");
    expect(metric).toMatchObject({ value_percent: 22.4, baseline_percent: 4.8, ratio_to_baseline: 4.7 });
  });
});

describe("loadConfig", () => {
  it("uses the documented defaults and mock rules", () => {
    const config = loadConfig({});
    expect(config).toMatchObject({ port: 8001, providerId: "anthropic", modelId: "claude-sonnet-5-5", mock: true });
    expect(loadConfig({ ANTHROPIC_API_KEY: "k" }).mock).toBe(false);
    expect(loadConfig({ ANTHROPIC_API_KEY: "k", MOCK_AGENT: "true" }).mock).toBe(true);
    expect(loadConfig({ PORT: "9100" }).port).toBe(9100);
  });
});
