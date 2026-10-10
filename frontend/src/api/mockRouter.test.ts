import { describe, expect, it } from "vitest";
import { resolveMock, MockRouteError } from "./mockRouter";
import { getBoothDetail, getFlags, getSummary, reviewFlag } from "./core";
import { chainStatus, createReport, fetchReportFile, getReport, listReports, verifyReport } from "./trust";
import { readFileText } from "../lib/readFile";

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
  });

  it("verifies by content: the original matches, anything else does not", async () => {
    const original = await fetchReportFile("VG-2026-0001");
    expect(original.name).toBe("VG-2026-0001.json");
    const match = await verifyReport(original);
    expect(match).toMatchObject({ status: "MATCH", report_id: "VG-2026-0001", superseded_by: "VG-2026-0002" });
    expect(match.computed_hash).toBe(match.onchain_hash);

    const text = await readFileText(original);
    const mismatch = await verifyReport(new File([`${text} `], "edited.json"));
    expect(mismatch.status).toBe("MISMATCH");
    expect(mismatch.computed_hash).not.toBe(mismatch.onchain_hash);

    const unknown = await verifyReport(new File(['{"report_id":"VG-2026-0999"}'], "x.json"));
    expect(unknown).toMatchObject({ status: "NOT_FOUND", onchain_hash: null, submitter: null });
    await expect(verifyReport(new File(["not json"], "x.json"))).rejects.toMatchObject({ status: 422 });
  });

  it("records corrections like the real service", async () => {
    const created = await createReport({ audit_id: "aud_001", reviewer_name: "R. Sharma", supersedes: "VG-2026-0002" });
    expect(created.report_id).toMatch(/^VG-\d{4}-0003$/);
    const items = (await listReports()).items;
    expect(items[0]?.report_id).toBe(created.report_id);
    expect(items.find((r) => r.report_id === "VG-2026-0002")?.superseded_by).toBe(created.report_id);
    await expect(
      createReport({ audit_id: "aud_001", reviewer_name: "R. Sharma", supersedes: "VG-2026-0002" }),
    ).rejects.toMatchObject({ status: 409, code: "ALREADY_SUPERSEDED" });
    await expect(fetchReportFile("VG-2026-0999")).rejects.toMatchObject({ status: 404 });
  });

  it("raises a clear error for unknown routes", () => {
    expect(() => resolveMock("core", "GET", "/api/unknown", undefined)).toThrow(MockRouteError);
    expect(() => resolveMock("core", "GET", "/api/unknown", undefined)).toThrow(/MOCK_ROUTE_NOT_FOUND/);
  });
});
