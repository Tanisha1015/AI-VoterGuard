import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import VerifyResult from "./VerifyResult";
import type { VerifyResult as VerifyResultData } from "../api/types";
import match from "../mocks/verify_match.json";
import mismatch from "../mocks/verify_mismatch.json";

function renderResult(result: VerifyResultData, simulated = false) {
  return render(
    <MemoryRouter>
      <VerifyResult result={result} simulated={simulated} />
    </MemoryRouter>,
  );
}

describe("VerifyResult", () => {
  it("MATCH shows the identical message with the recorded time, icon and submitter", () => {
    renderResult(match as VerifyResultData);
    const card = screen.getByTestId("verify-result");
    expect(card).toHaveAttribute("data-status", "MATCH");
    expect(within(card).getByRole("heading", { name: "Identical to the recorded report" })).toBeInTheDocument();
    expect(within(card).getByText(/^This file is identical to the report recorded on .*2026.*UTC\.$/)).toBeInTheDocument();
    expect(within(card).getByText("✓")).toBeInTheDocument();
    expect(within(card).getByText("0x7099…79c8")).toBeInTheDocument();
    expect(within(card).queryByTestId("computed-hash")).not.toBeInTheDocument();
  });

  it("MISMATCH shows both hashes, shortened and copyable", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    renderResult(mismatch as VerifyResultData);
    const card = screen.getByTestId("verify-result");
    expect(within(card).getByRole("heading", { name: "Different from the recorded report" })).toBeInTheDocument();
    expect(within(card).getByText(/This file is different from the recorded report/)).toBeInTheDocument();
    expect(within(card).getByText("✕")).toBeInTheDocument();
    expect(within(card).getByTestId("computed-hash")).toHaveTextContent("0x2242…0cc1");
    expect(within(card).getByTestId("onchain-hash")).toHaveTextContent("0xc265…74bf");

    await user.click(within(card).getByRole("button", { name: "Copy recorded hash" }));
    expect(writeText).toHaveBeenCalledWith(mismatch.onchain_hash);
    writeText.mockRestore();
  });

  it("NOT_FOUND renders a neutral card without hashes", () => {
    renderResult({ report_id: "VG-2026-0999", status: "NOT_FOUND", computed_hash: mismatch.computed_hash,
      onchain_hash: null, recorded_at: null, submitter: null, superseded_by: null });
    const card = screen.getByTestId("verify-result");
    expect(within(card).getByText("No report with the id VG-2026-0999 is recorded on the ledger.")).toBeInTheDocument();
    expect(within(card).getAllByText("Not recorded").length).toBeGreaterThan(0);
  });

  it("links to the superseding report and labels simulations", () => {
    renderResult({ ...(match as VerifyResultData), superseded_by: "VG-2026-0002" }, true);
    expect(screen.getByText(/Simulation: this result is for a deliberately changed copy/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View report VG-2026-0002" })).toHaveAttribute(
      "href", "/verify?report_id=VG-2026-0002",
    );
  });
});
