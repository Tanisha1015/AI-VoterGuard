import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import * as core from "../api/core";
import { ApiError, NetworkError } from "../api/client";

async function fillAndSubmit(name: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Your name"), name);
  await user.type(screen.getByLabelText("Father's, mother's or husband's name"), "Ramesh Kumar");
  await user.type(screen.getByLabelText("Part (booth) number"), "17");
  await user.click(screen.getByRole("button", { name: "Check my entry" }));
  return user;
}

async function resultRegion() {
  const region = screen.getByRole("region", { name: "Lookup result" });
  await within(region).findByRole("article");
  return region;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Citizen page results (mocks)", () => {
  it("PRESENT", async () => {
    renderApp("/");
    await fillAndSubmit("Meena Kumari");
    const region = await resultRegion();
    expect(within(region).getByText("Your name is in the final roll")).toBeInTheDocument();
    expect(within(region).getByText("VGX****219")).toBeInTheDocument();
  });

  it("REMOVED shows masked EPIC, part, reason, steps, deadline and disclaimer", async () => {
    const spy = vi.spyOn(core, "citizenLookup");
    renderApp("/");
    await fillAndSubmit("Sunita Devi");
    const region = await resultRegion();

    expect(spy).toHaveBeenCalledWith({
      name: "Sunita Devi",
      relative_name: "Ramesh Kumar",
      part_no: 17,
      epic_no: null,
      lang: "en",
    });
    expect(within(region).getByText("Your entry is not in the final roll")).toBeInTheDocument();
    expect(within(region).getByText("VGX****482")).toBeInTheDocument();
    expect(within(region).getByText("17")).toBeInTheDocument();
    expect(within(region).getByText("Recorded as having moved to a different address")).toBeInTheDocument();
    expect(within(region).getByRole("heading", { name: "What you can do" })).toBeInTheDocument();
    expect(within(region).getByText("Keep a proof of your current address ready")).toBeInTheDocument();
    expect(within(region).getByText("2026-10-31")).toBeInTheDocument();
    expect(
      within(region).getByText("Confirm current forms and deadlines on the official ECI website."),
    ).toBeInTheDocument();
  });

  it("ADDED", async () => {
    renderApp("/");
    await fillAndSubmit("Arjun added");
    const region = await resultRegion();
    expect(within(region).getByText("Your name has been added")).toBeInTheDocument();
  });

  it("NOT_FOUND suggests checking spelling or using EPIC", async () => {
    renderApp("/");
    const user = await fillAndSubmit("Nonexistent Person");
    const region = await resultRegion();
    expect(within(region).getByText("We could not find a matching entry")).toBeInTheDocument();
    expect(within(region).getByText(/check the spelling/)).toBeInTheDocument();
    await user.click(within(region).getByRole("button", { name: "Search with EPIC number" }));
    expect(screen.getByLabelText("EPIC number")).toBeInTheDocument();
  });

  it("AMBIGUOUS asks for EPIC and lists no candidates", async () => {
    renderApp("/");
    await fillAndSubmit("Ambiguous Name");
    const region = await resultRegion();
    expect(within(region).getByText("More than one entry matches")).toBeInTheDocument();
    expect(within(region).getByText(/search again using your EPIC number/)).toBeInTheDocument();
    expect(within(region).queryByText(/VGX\*/)).not.toBeInTheDocument();
  });

  it("shows a friendly message on HTTP 429", async () => {
    vi.spyOn(core, "citizenLookup").mockRejectedValue(new ApiError(429, "RATE_LIMITED", "Too many"));
    renderApp("/");
    await fillAndSubmit("Meena");
    expect(await screen.findByRole("alert")).toHaveTextContent("Please wait a minute and try again.");
  });

  it("shows a friendly message on network error", async () => {
    vi.spyOn(core, "citizenLookup").mockRejectedValue(new NetworkError());
    renderApp("/");
    await fillAndSubmit("Meena");
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not reach the service.");
  });
});
