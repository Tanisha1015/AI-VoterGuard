import { describe, expect, it } from "vitest";
import { FIXTURE_REQUEST } from "./fixtures.js";
import { checkNeutrality, checkText, findBlockedTerms } from "./guard.js";
import { extractNumbers } from "./numbers.js";
import type { ExplainContent } from "./types.js";

const P = FIXTURE_REQUEST;

function content(en: string, hi = "यह असामान्य है और सत्यापन के योग्य है।"): ExplainContent {
  const check = { en: "Recommend a field check.", hi: "क्षेत्रीय जाँच की सिफारिश की जाती है।" };
  return { explanation: { en, hi }, recommended_checks: [check, check] };
}

describe("blocklist", () => {
  it("rejects English loaded words, case-insensitively", () => {
    expect(checkText("this is fraud", P).passed).toBe(false);
    expect(findBlockedTerms("This is FRAUDULENT and Rigged")).toEqual(
      expect.arrayContaining(["fraudulent", "rigged"]),
    );
  });

  it("rejects Hindi loaded words including nukta variants", () => {
    expect(checkText("फर्जी", P).passed).toBe(false);
    expect(findBlockedTerms("यह फ़र्ज़ी प्रविष्टि है")).not.toHaveLength(0);
    expect(findBlockedTerms("यह अवैध है")).not.toHaveLength(0);
    expect(findBlockedTerms("धोखाधड़ी")).not.toHaveLength(0);
  });

  it("covers every required term", () => {
    const english = "fraud fraudulent illegal illegally rigging rigged fake bogus ineligible foreigner infiltrator scam conspiracy";
    for (const word of english.split(" ")) {
      expect(findBlockedTerms(`a ${word} here`), word).not.toHaveLength(0);
    }
    for (const word of ["धोखाधड़ी", "फर्जी", "अवैध", "घुसपैठिया", "घोटाला", "साजिश", "विदेशी"]) {
      expect(findBlockedTerms(word), word).not.toHaveLength(0);
    }
  });

  it("matches whole words only", () => {
    expect(findBlockedTerms("A fakery of words, fraudster-free text")).toEqual([]);
    expect(findBlockedTerms("The unusual pattern is worth verifying.")).toEqual([]);
  });
});

describe("number check", () => {
  it("rejects an invented number", () => {
    const result = checkText("Booth 17 shows a deletion rate of 98%.", P);
    expect(result.passed).toBe(false);
    expect(result.violations.join(" ")).toContain("98%");
  });

  it("accepts numbers that come from the payload", () => {
    const text = "Booth 17 shows a deletion rate of 22.4%, compared with a baseline of 4.8%, about 4.7 times as high.";
    expect(checkText(text, P)).toEqual({ passed: true, violations: [] });
  });

  it("allows rounding, fraction forms and Devanagari digits", () => {
    expect(checkText("The rate is 22% against 5%.", P).passed).toBe(true);
    expect(checkText("The rate is 0.224 against 0.048.", P).passed).toBe(true);
    expect(checkText("भाग संख्या १७ में दर २२.४% है।", P).passed).toBe(true);
    expect(checkText("There are 182 removed entries out of 812.", P).passed).toBe(true);
  });

  it("rejects a percent that only matches a count", () => {
    expect(checkText("About 182% were removed.", P).passed).toBe(false);
  });

  it("ignores age-band labels", () => {
    expect(extractNumbers("ages 18-25 and 80+")).toEqual([]);
  });
});

describe("checkNeutrality", () => {
  it("passes clean bilingual content", () => {
    const ok = content("Booth 17 shows a deletion rate of 22.4%. This is unusual and worth verifying.");
    expect(checkNeutrality(ok, P)).toEqual({ passed: true, violations: [] });
  });

  it("reports the field of each violation", () => {
    const result = checkNeutrality(content("This is fraud at 98%.", "यह फर्जी है।"), P);
    expect(result.passed).toBe(false);
    expect(result.violations.join("\n")).toContain("explanation.en");
    expect(result.violations.join("\n")).toContain("explanation.hi");
  });

  it("requires Hindi fields to be in Devanagari", () => {
    const result = checkNeutrality(content("Booth 17 is unusual.", "Booth 17 is unusual."), P);
    expect(result.passed).toBe(false);
  });
});
