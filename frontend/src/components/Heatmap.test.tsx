import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import booths from "../mocks/booths.json";

describe("Heatmap", () => {
  it("renders one tile per booth, each linking to its booth page", async () => {
    renderApp("/reviewer");
    const grid = await screen.findByTestId("heatmap");
    const tiles = within(grid).getAllByTestId("heatmap-tile");

    expect(tiles).toHaveLength(booths.items.length);
    for (const booth of booths.items) {
      const tile = within(grid).getByRole("link", { name: new RegExp(`^Booth ${booth.part_no}, risk score ${booth.risk_score}`) });
      expect(tile).toHaveAttribute("href", `/reviewer/booth/${booth.part_no}`);
    }
  });

  it("marks flagged booths in the accessible label, not only by colour", async () => {
    renderApp("/reviewer");
    expect(await screen.findByRole("link", { name: "Booth 17, risk score 87, 3 flag(s), worth verifying" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Booth 8, risk score 52, no flags" })).toBeInTheDocument();
  });

  it("navigates to the booth detail page when a tile is activated", async () => {
    const user = userEvent.setup();
    renderApp("/reviewer");
    await user.click(await screen.findByRole("link", { name: /^Booth 17, risk score 87/ }));
    expect(await screen.findByRole("heading", { level: 1, name: "Booth 17" })).toBeInTheDocument();
  });
});
