import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import * as trust from "../api/trust";
import { ApiError } from "../api/client";

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
    expect(within(card).getByText("VG-2026-0001")).toBeInTheDocument();
    expect(within(card).getByText("0xc265…74bf")).toHaveAttribute(
      "title",
      "0xc265421957a9e0738c37d6a6e567c8dd32d9b7e2f68aa23ea8c0fc3ccbd174bf",
    );
    expect(within(card).getByText("0x40fa…89c8")).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: "Download JSON" })).toHaveAttribute(
      "href",
      expect.stringMatching(/\/files\/VG-2026-0001\.json$/),
    );
    expect(within(card).getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      expect.stringMatching(/\/files\/VG-2026-0001\.pdf$/),
    );
    expect(within(card).getByRole("link", { name: "Verify this report" })).toHaveAttribute(
      "href",
      "/verify?report_id=VG-2026-0001",
    );
  });

  it("copies the full report hash to the clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    const panel = await openPanel();
    await user.type(within(panel).getByLabelText("Reviewer name"), "R. Sharma");
    await user.click(within(panel).getByRole("button", { name: "Finalize and record report" }));
    const card = await within(panel).findByTestId("report-card");

    await user.click(within(card).getByRole("button", { name: "Copy hash" }));
    expect(writeText).toHaveBeenCalledWith("0xc265421957a9e0738c37d6a6e567c8dd32d9b7e2f68aa23ea8c0fc3ccbd174bf");
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
