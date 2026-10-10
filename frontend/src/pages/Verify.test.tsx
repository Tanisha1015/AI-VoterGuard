import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import * as trust from "../api/trust";
import { readFileText } from "../lib/readFile";

afterEach(() => {
  vi.restoreAllMocks();
});

const row = (id: string) => screen.findByTestId(`report-row-${id}`);

describe("Verify page", () => {
  it("pre-selects the report from ?report_id= and shows the explanation", async () => {
    renderApp("/verify?report_id=VG-2026-0001");
    expect(await row("VG-2026-0001")).toHaveAttribute("aria-current", "true");
    expect(within(await row("VG-2026-0001")).getByText("Superseded by VG-2026-0002")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Verify report VG-2026-0001" })).toBeInTheDocument();
    expect(screen.getByText(/the file has not changed since it was recorded/)).toBeInTheDocument();
    expect(screen.getByText(/that the findings are correct or that any removal was or was not appropriate/)).toBeInTheDocument();
  });

  it("load original then verify gives MATCH", async () => {
    const user = userEvent.setup();
    renderApp("/verify?report_id=VG-2026-0002");
    await user.click(await screen.findByRole("button", { name: "Load original" }));
    expect(await screen.findByText(/^File ready: VG-2026-0002\.json/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Verify" }));

    const result = await screen.findByTestId("verify-result");
    expect(result).toHaveAttribute("data-status", "MATCH");
    expect(within(result).queryByText(/Simulation/)).not.toBeInTheDocument();
  });

  it("simulate tampering changes one character of the file and shows a labelled MISMATCH", async () => {
    const spy = vi.spyOn(trust, "verifyReport");
    const user = userEvent.setup();
    renderApp("/verify?report_id=VG-2026-0002");
    expect(screen.queryByRole("button", { name: /Simulate tampering/ })).not.toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Load original" }));
    await user.click(await screen.findByRole("button", { name: /Simulate tampering/ }));

    const result = await screen.findByTestId("verify-result");
    expect(result).toHaveAttribute("data-status", "MISMATCH");
    expect(within(result).getByText(/Simulation: this result is for a deliberately changed copy/)).toBeInTheDocument();
    expect(screen.getByTestId("tamper-note")).toHaveTextContent(/^Simulation: changed character \d+ from “\d” to “\d”\.$/);

    const original = await readFileText(await trust.fetchReportFile("VG-2026-0002"));
    const sent = await readFileText(spy.mock.calls.at(-1)?.[0] as File);
    expect(sent).not.toBe(original);
    expect(sent.length).toBe(original.length);
    expect([...sent].filter((ch, i) => ch !== original[i])).toHaveLength(1);
  });

  it("recording a corrected version marks the old report Superseded and adds the new one on top", async () => {
    const spy = vi.spyOn(trust, "createReport");
    const user = userEvent.setup();
    renderApp("/verify?report_id=VG-2026-0002");
    expect(within(await row("VG-2026-0002")).getByText("Latest version")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Reviewer name"), "R. Sharma");
    await user.click(screen.getByRole("button", { name: "Record corrected version" }));

    expect(await within(await row("VG-2026-0002")).findByText("Superseded by VG-2026-0003")).toBeInTheDocument();
    expect(spy).toHaveBeenCalledWith({ audit_id: "aud_001", reviewer_name: "R. Sharma", supersedes: "VG-2026-0002" });
    const ids = within(screen.getByTestId("report-list")).getAllByRole("button").map((b) => b.getAttribute("data-testid"));
    expect(ids[0]).toBe("report-row-VG-2026-0003");
    expect(within(await row("VG-2026-0003")).getByText("Latest version")).toBeInTheDocument();
    await waitFor(async () => expect(await row("VG-2026-0003")).toHaveAttribute("aria-current", "true"));
    expect(screen.getByTestId("correction-notice")).toHaveTextContent("Recorded VG-2026-0003. It now supersedes VG-2026-0002.");
    expect(screen.getByRole("heading", { name: "Verify report VG-2026-0003" })).toBeInTheDocument();
  });

  it("does not offer a correction for a report that is already superseded", async () => {
    renderApp("/verify?report_id=VG-2026-0001");
    expect(await screen.findByText(/already been replaced by VG-2026-0002/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record corrected version" })).not.toBeInTheDocument();
  });

  it("verifies an uploaded file and asks for a report selection first", async () => {
    const user = userEvent.setup();
    renderApp("/verify");
    expect(await screen.findByText("Select a report from the list to begin.")).toBeInTheDocument();
    await user.click(await row("VG-2026-0002"));
    const upload = new File(['{"report_id":"VG-2026-0002","edited":true}'], "copy.json", { type: "application/json" });
    await user.upload(screen.getByLabelText("Upload a report file (.json)"), upload);
    await user.click(screen.getByRole("button", { name: "Verify" }));
    expect(await screen.findByTestId("verify-result")).toHaveAttribute("data-status", "MISMATCH");
  });
});
