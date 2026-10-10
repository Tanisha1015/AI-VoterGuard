import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import { filterBooths, sortBooths } from "../lib/booths";
import booths from "../mocks/booths.json";
import flags from "../mocks/flags.json";
import type { BoothSummary, Flag } from "../api/types";

const B = booths.items as BoothSummary[];
const F = flags.items as Flag[];

function rowParts(): string[] {
  return screen.getAllByTestId("booth-row").map((row) => within(row).getAllByRole("link")[0]?.textContent?.replace("⚑", "").trim() ?? "");
}

describe("booth helpers", () => {
  it("filters by flag detector and severity", () => {
    expect(filterBooths(B, F, "", "HOUSE_CLUSTER").map((b) => b.part_no)).toEqual([42]);
    expect(filterBooths(B, F, "HIGH", "").map((b) => b.part_no)).toEqual([17]);
    expect(filterBooths(B, F, "", "")).toHaveLength(B.length);
  });

  it("sorts ascending and descending", () => {
    expect(sortBooths(B, "part_no", "asc")[0]?.part_no).toBe(5);
    expect(sortBooths(B, "removed", "desc")[0]?.part_no).toBe(17);
  });
});

describe("BoothTable", () => {
  it("sorts by a column via keyboard-accessible header buttons", async () => {
    const user = userEvent.setup();
    renderApp("/reviewer");
    await screen.findAllByTestId("booth-row");
    expect(rowParts()[0]).toBe("17"); // default: risk score descending

    const sortPart = screen.getByRole("button", { name: "Sort by Part" });
    sortPart.focus();
    await user.keyboard("{Enter}");
    expect(rowParts()).toEqual(["5", "8", "17", "23", "31", "42", "54", "60"]);
    expect(sortPart.closest("th")).toHaveAttribute("aria-sort", "ascending");
  });

  it("filters by detector", async () => {
    const user = userEvent.setup();
    renderApp("/reviewer");
    await screen.findAllByTestId("booth-row");
    await user.selectOptions(screen.getByLabelText("Flag type"), "HOUSE_CLUSTER");
    expect(rowParts()).toEqual(["42"]);
  });
});
