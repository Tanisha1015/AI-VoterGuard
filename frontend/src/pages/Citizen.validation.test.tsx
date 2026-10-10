import { afterEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import * as core from "../api/core";
import { buildRequest, validate } from "./citizenForm";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("validate()", () => {
  it("requires all name-mode fields", () => {
    expect(validate({ name: "", relative_name: "", part_no: "", epic_no: "" }, false)).toEqual({
      name: "citizen.errors.name_required",
      relative_name: "citizen.errors.relative_name_required",
      part_no: "citizen.errors.part_no_required",
    });
  });

  it("rejects a non-numeric part number", () => {
    expect(validate({ name: "a", relative_name: "b", part_no: "1x", epic_no: "" }, false)).toEqual({
      part_no: "citizen.errors.part_no_invalid",
    });
  });

  it("only requires EPIC in EPIC mode", () => {
    expect(validate({ name: "", relative_name: "", part_no: "", epic_no: "" }, true)).toEqual({
      epic_no: "citizen.errors.epic_required",
    });
  });

  it("builds an EPIC-only request", () => {
    expect(buildRequest({ name: "x", relative_name: "y", part_no: "1", epic_no: " vgx1234567 " }, true, "hi")).toEqual({
      name: null,
      relative_name: null,
      part_no: null,
      epic_no: "VGX1234567",
      lang: "hi",
    });
  });
});

describe("Citizen page validation", () => {
  it("shows inline errors for every empty required field and does not call the API", async () => {
    const spy = vi.spyOn(core, "citizenLookup");
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("button", { name: "Check my entry" }));

    expect(screen.getByText("Please enter your name.")).toBeInTheDocument();
    expect(screen.getByText("Please enter the relative's name.")).toBeInTheDocument();
    expect(screen.getByText("Please enter the part number.")).toBeInTheDocument();
    expect(screen.getByLabelText("Your name")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Your name")).toHaveFocus();
    expect(spy).not.toHaveBeenCalled();
  });

  it("switches to a single EPIC field and validates it", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("switch", { name: "Use my EPIC number instead" }));

    expect(screen.queryByLabelText("Your name")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Check my entry" }));
    expect(screen.getByText("Please enter your EPIC number.")).toBeInTheDocument();
  });
});
