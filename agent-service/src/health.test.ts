import { describe, expect, it } from "vitest";
import { loadConfig } from "./config.js";
import { buildApp } from "./index.js";

describe("GET /health", () => {
  it("reports ok in mock mode", async () => {
    const app = await buildApp(loadConfig({ MOCK_AGENT: "true" }));
    const res = await app.inject({ method: "GET", url: "/health" });
    expect(res.statusCode).toBe(200);
    expect(res.json()).toEqual({ status: "ok", mode: "mock" });
    await app.close();
  });

  it("reports agent mode when a key is set and mock is off", async () => {
    const app = await buildApp(loadConfig({ ANTHROPIC_API_KEY: "test-key" }));
    const res = await app.inject({ method: "GET", url: "/health" });
    expect(res.json()).toEqual({ status: "ok", mode: "agent" });
    await app.close();
  });
});
