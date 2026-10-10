import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "../test/renderApp";

describe("BoothDetail", () => {
  it("switching language updates the flag explanation text", async () => {
    const user = userEvent.setup();
    renderApp("/reviewer/booth/17");

    const explanation = await screen.findByTestId("explanation-f_17_1");
    expect(explanation).toHaveTextContent(
      "Booth 17 shows a deletion rate of 22.4%, compared with a constituency baseline of 4.8%. This is unusual and worth verifying.",
    );

    await user.click(screen.getByRole("button", { name: "हिन्दी" }));

    expect(await screen.findByTestId("explanation-f_17_1")).toHaveTextContent(
      "भाग संख्या 17 में नाम हटाने की दर 22.4% है, जबकि निर्वाचन क्षेत्र का आधारभूत औसत 4.8% है। यह असामान्य है और सत्यापन के योग्य है।",
    );
    expect(screen.getByRole("heading", { name: "निर्वाचन क्षेत्र की तुलना में हटाने की दर" })).toBeInTheDocument();
    expect(screen.getAllByText("एआई-सहायता प्राप्त").length).toBeGreaterThan(0);
    expect(
      screen.getByText("ये संकेत क्षेत्रीय सत्यापन के लिए सुझाव मात्र हैं। ये किसी अनियमितता या पात्रता को स्थापित नहीं करते।"),
    ).toBeInTheDocument();
  });

  it("shows booth stats and the three charts", async () => {
    renderApp("/reviewer/booth/17");
    expect(await screen.findByRole("figure", { name: "Recorded reasons (share of removals)" })).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: "Removals by gender (count)" })).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: "Removals by age group (share)" })).toBeInTheDocument();
    expect(screen.getByText("22.4%")).toBeInTheDocument();
  });

  it("shows a not-found message for a booth outside the audit", async () => {
    renderApp("/reviewer/booth/999");
    expect(await screen.findByText("This booth was not found in the current audit.")).toBeInTheDocument();
  });
});
