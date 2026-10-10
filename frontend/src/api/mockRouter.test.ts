import { describe, expect, it } from "vitest";
import { resolveMock, MockRouteError } from "./mockRouter";
import { getBoothDetail, getFlags, getSummary, reviewFlag } from "./core";
import { chainStatus, getReport, listReports, verifyReport } from "./trust";

describe("mock router", () => {
  it("serves core fixtures", async () => {
    expect((await getSummary()).audit_id).toBe("aud_001");
    expect((await getBoothDetail(17)).flags.length).toBe(3);
    expect((await getFlags({ part_no: 17 })).items.every((f) => f.part_no === 17)).toBe(true);
    const updated = await reviewFlag("f_17_1", { status: "ACCEPTED", note: "Field check scheduled" });
    expect(updated.review.status).toBe("ACCEPTED");
  });

  it("serves trust fixtures", async () => {
    expect((await listReports()).items).toHaveLength(2);
    expect((await getReport("VG-2026-0001")).superseded_by).toBe("VG-2026-0002");
    expect((await chainStatus()).chain_id).toBe(31337);
    const match = await verifyReport(new File(["{}"], "VG-2026-0001.json"));
    expect(match.status).toBe("MATCH");
    const mismatch = await verifyReport(new File(["{}"], "tampered.json"));
    expect(mismatch.status).toBe("MISMATCH");
  });

  it("raises a clear error for unknown routes", () => {
    expect(() => resolveMock("core", "GET", "/api/unknown", undefined)).toThrow(MockRouteError);
    expect(() => resolveMock("core", "GET", "/api/unknown", undefined)).toThrow(/MOCK_ROUTE_NOT_FOUND/);
  });
});
