import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import * as core from "../api/core";
import { ApiError } from "../api/client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ReviewControls", () => {
  it("accepting a flag updates the saved status in the UI", async () => {
    const user = userEvent.setup();
    renderApp("/reviewer/booth/17");
    const card = await screen.findByTestId("flag-f_17_1");
    const status = within(card).getByTestId("review-status-f_17_1");
    expect(status).toHaveTextContent("Pending");

    await user.type(within(card).getByLabelText("Reviewer note (optional)"), "Field check scheduled");
    await user.click(within(card).getByRole("button", { name: "Accept" }));

    expect(await within(card).findByText("Accepted for field check")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Accept" })).toHaveAttribute("aria-pressed", "true");
    expect(await within(card).findByText(/^Saved /)).toBeInTheDocument();
    // other flags are untouched
    expect(screen.getByTestId("review-status-f_17_2")).toHaveTextContent("Pending");
  });

  it("rolls back the optimistic update when saving fails", async () => {
    vi.spyOn(core, "reviewFlag").mockRejectedValue(new ApiError(500, "SERVER_ERROR", "boom"));
    const user = userEvent.setup();
    renderApp("/reviewer/booth/17");
    const card = await screen.findByTestId("flag-f_17_1");

    await user.click(within(card).getByRole("button", { name: "Not taken forward" }));

    expect(await within(card).findByRole("alert")).toHaveTextContent("could not be saved");
    expect(within(card).getByTestId("review-status-f_17_1")).toHaveTextContent("Pending");
    expect(within(card).getByRole("button", { name: "Not taken forward" })).toHaveAttribute("aria-pressed", "false");
  });

  it("shows the flag disclaimer, detector label, severity text and source badge", async () => {
    renderApp("/reviewer/booth/42");
    const card = await screen.findByTestId("flag-f_42_1");
    expect(within(card).getByRole("heading", { name: "Removals concentrated in few houses" })).toBeInTheDocument();
    expect(within(card).getByText("Medium")).toBeInTheDocument();
    expect(within(card).getByText("Template")).toBeInTheDocument();
    expect(within(card).getByText("Share from a few house numbers: 38.0% (constituency baseline 6.0%)")).toBeInTheDocument();
    expect(
      screen.getByText("Flags are prompts for field verification. They do not establish wrongdoing or eligibility."),
    ).toBeInTheDocument();
  });
});
