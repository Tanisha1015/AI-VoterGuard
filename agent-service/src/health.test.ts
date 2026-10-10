import { describe, expect, it } from "vitest";
import { buildApp } from "./index.js";

describe("GET /health", () => {
  it("reports ok in mock mode", async () => {
    const app = await buildApp();
    const res = await app.inject({ method: "GET", url: "/health" });
    expect(res.statusCode).toBe(200);
    expect(res.json()).toEqual({ status: "ok", mode: "mock" });
    await app.close();
  });
});
