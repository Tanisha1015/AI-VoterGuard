import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import * as trust from "../api/trust";
import { ApiError } from "../api/client";
import { shortHash } from "../lib/format";

afterEach(() => {
  vi.restoreAllMocks();
});

async function openPanel() {
  renderApp("/reviewer");
  return screen.findByRole("region", { name: "Finalize and record report" });
}

describe("FinalizePanel", () => {
  it("requires a reviewer name and shows a gentle pending note", async () => {
    const spy = vi.spyOn(trust, "createReport");
    const user = userEvent.setup();
    const panel = await openPanel();

    expect(within(panel).getByTestId("finalize-pending")).toHaveTextContent("Pending reviews: 9");
    expect(within(panel).getByText(/You can still finalize/)).toBeInTheDocument();

    await user.click(within(panel).getByRole("button", { name: "Finalize and record report" }));
    expect(within(panel).getByText("Please enter the reviewer name.")).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });

  it("records the report and shows the report card from the mock", async () => {
    const spy = vi.spyOn(trust, "createReport");
    const user = userEvent.setup();
    const panel = await openPanel();

    await user.type(within(panel).getByLabelText("Reviewer name"), "R. Sharma");
    await user.click(within(panel).getByRole("button", { name: "Finalize and record report" }));

    const card = await within(panel).findByTestId("report-card");
    expect(spy).toHaveBeenCalledWith({ audit_id: "aud_001", reviewer_name: "R. Sharma", supersedes: null });
    const created = await (spy.mock.results[0]?.value as ReturnType<typeof trust.createReport>);
    const id = created.report_id;
    expect(id).toMatch(/^VG-\d{4}-0003$/); // mock store already holds 0001 and 0002
    expect(within(card).getByText(id)).toBeInTheDocument();
    expect(within(card).getByText(shortHash(created.report_hash))).toHaveAttribute("title", created.report_hash);
    expect(within(card).getByText("0x40fa…89c8")).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: "Download JSON" })).toHaveAttribute(
      "href",
      expect.stringMatching(new RegExp(`/files/${id}\\.json$`)),
    );
    expect(within(card).getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      expect.stringMatching(new RegExp(`/files/${id}\\.pdf$`)),
    );
    expect(within(card).getByRole("link", { name: "Verify this report" })).toHaveAttribute(
      "href",
      `/verify?report_id=${id}`,
    );
  });

  it("copies the full report hash to the clipboard", async () => {
    const spy = vi.spyOn(trust, "createReport");
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    const panel = await openPanel();
    await user.type(within(panel).getByLabelText("Reviewer name"), "R. Sharma");
    await user.click(within(panel).getByRole("button", { name: "Finalize and record report" }));
    const card = await within(panel).findByTestId("report-card");
    const created = await (spy.mock.results[0]?.value as ReturnType<typeof trust.createReport>);

    await user.click(within(card).getByRole("button", { name: "Copy hash" }));
    expect(writeText).toHaveBeenCalledWith(created.report_hash);
    expect(await within(card).findByText("Copied")).toBeInTheDocument();
  });

  it("explains a 502 from the trust service clearly", async () => {
    vi.spyOn(trust, "createReport").mockRejectedValue(new ApiError(502, "CHAIN_UNAVAILABLE", "Bad gateway"));
    const user = userEvent.setup();
    const panel = await openPanel();
    await user.type(within(panel).getByLabelText("Reviewer name"), "R. Sharma");
    await user.click(within(panel).getByRole("button", { name: "Finalize and record report" }));

    expect(await within(panel).findByRole("alert")).toHaveTextContent("Nothing was recorded");
    expect(within(panel).queryByTestId("report-card")).not.toBeInTheDocument();
  });
});
