import { afterEach, describe, expect, it } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, NetworkError } from "../api/client";
import { clearToasts, pushToast, toastKeyFor } from "../lib/toast";
import { renderApp } from "../test/renderApp";
import Toaster from "./Toaster";
import { EmptyState } from "./QueryState";
import "../i18n";

afterEach(() => {
  act(() => clearToasts());
});

describe("toasts", () => {
  it("maps request failures to calm toast keys", () => {
    expect(toastKeyFor(new NetworkError())).toBe("toast.network");
    expect(toastKeyFor(new ApiError(429, "RATE_LIMITED", "x"))).toBe("toast.rate_limited");
    expect(toastKeyFor(new ApiError(502, "CHAIN_UNAVAILABLE", "x"))).toBe("toast.ledger");
    expect(toastKeyFor(new ApiError(500, "X", "x"))).toBe("toast.generic");
    expect(toastKeyFor(new Error("boom"))).toBe("toast.generic");
  });

  it("shows a toast in a polite live region and dismisses it with the button", async () => {
    const user = userEvent.setup();
    const { container } = render(<Toaster />);

    act(() => pushToast("toast.network"));
    expect(await screen.findByText("No connection to the service.")).toBeInTheDocument();
    expect(container.querySelector('[aria-live="polite"]')).not.toBeNull();

    await user.click(screen.getByRole("button", { name: "Dismiss notice" }));
    expect(screen.queryByText("No connection to the service.")).not.toBeInTheDocument();
  });

  it("keeps at most three toasts", () => {
    render(<Toaster />);
    act(() => {
      pushToast("toast.network");
      pushToast("toast.generic");
      pushToast("toast.ledger");
      pushToast("toast.rate_limited");
    });
    expect(screen.getAllByTestId("toast-text")).toHaveLength(3);
    expect(screen.queryByText("No connection to the service.")).not.toBeInTheDocument();
  });
});

describe("empty state and page titles", () => {
  it("renders an empty state with a title and hint", () => {
    render(<EmptyState title="Nothing here" hint="Try later" testId="empty" />);
    expect(screen.getByTestId("empty")).toHaveTextContent("Nothing here");
    expect(screen.getByTestId("empty")).toHaveTextContent("Try later");
  });

  it.each([
    ["/", "Check your entry in the roll · VoterGuard India"],
    ["/verify", "Verify a report · VoterGuard India"],
    ["/nope", "Page not found · VoterGuard India"],
  ])("sets the document title for %s", async (route, title) => {
    renderApp(route);
    await screen.findByRole("heading", { level: 1 });
    expect(document.title).toBe(title);
  });

  it("sets the booth title on the booth page", async () => {
    renderApp("/reviewer/booth/17");
    await screen.findByRole("heading", { name: "Booth 17" });
    expect(document.title).toBe("Booth 17 · VoterGuard India");
  });
});
