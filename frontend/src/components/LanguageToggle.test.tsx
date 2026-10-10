import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";
import { LANG_STORAGE_KEY } from "../i18n";

describe("Language toggle", () => {
  it("switches visible text to Hindi and persists the choice", async () => {
    const user = userEvent.setup();
    renderApp("/");

    expect(screen.getByRole("heading", { name: "Check your entry in the roll" })).toBeInTheDocument();
    expect(screen.getByText("Demo using synthetic data. This tool does not decide anyone's eligibility.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "हिन्दी" }));

    expect(await screen.findByRole("heading", { name: "मतदाता सूची में अपनी प्रविष्टि देखें" })).toBeInTheDocument();
    expect(screen.getByText("यह कृत्रिम (सिंथेटिक) डेटा पर आधारित डेमो है। यह टूल किसी की पात्रता तय नहीं करता।")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "नागरिक" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "हिन्दी" })).toHaveAttribute("aria-pressed", "true");
    expect(window.localStorage.getItem(LANG_STORAGE_KEY)).toBe("hi");
    expect(document.documentElement.lang).toBe("hi");
  });

  it("renders bilingual API fields in the active language", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("button", { name: "हिन्दी" }));

    await user.type(screen.getByLabelText("आपका नाम"), "Sunita Devi");
    await user.type(screen.getByLabelText("पिता, माता या पति का नाम"), "Ramesh");
    await user.type(screen.getByLabelText("भाग (बूथ) संख्या"), "17");
    await user.click(screen.getByRole("button", { name: "मेरी प्रविष्टि देखें" }));

    const region = screen.getByRole("region", { name: "खोज का परिणाम" });
    expect(await within(region).findByText("अपने वर्तमान पते का प्रमाण तैयार रखें")).toBeInTheDocument();
  });
});
