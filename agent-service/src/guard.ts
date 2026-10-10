import { BLOCKED_ENGLISH, BLOCKED_HINDI } from "./blocklist.js";
import { allowedNumbers, findUnsupportedNumbers, stripNukta } from "./numbers.js";
import type { ExplainContent, ExplainRequest } from "./types.js";

/**
 * Deterministic neutrality guard: (a) blocklist of loaded words in English and Hindi,
 * (b) number check, where every number in the text must come from the request payload.
 */

export interface GuardResult {
  passed: boolean;
  violations: string[];
}

const DEVANAGARI = /[\u0900-\u097F]/;
const WORD_EDGE_BEFORE = "(?<![\\p{L}\\p{N}_])";
const WORD_EDGE_AFTER = "(?![\\p{L}\\p{N}_])";

function englishPattern(terms: readonly string[]): RegExp {
  const alternatives = terms.map((t) => t.trim().replace(/\s+/g, "\\s+")).join("|");
  return new RegExp(`${WORD_EDGE_BEFORE}(?:${alternatives})${WORD_EDGE_AFTER}`, "giu");
}

const ENGLISH_PATTERN = englishPattern(BLOCKED_ENGLISH);
const HINDI_TERMS = [...new Set(BLOCKED_HINDI.map(stripNukta))];

/** Blocked terms found in one text (English whole-word, Hindi stem). */
export function findBlockedTerms(text: string): string[] {
  const found = new Set<string>();
  for (const match of text.matchAll(ENGLISH_PATTERN)) {
    found.add(match[0].toLowerCase().replace(/\s+/g, " "));
  }
  const hindi = stripNukta(text);
  for (const term of HINDI_TERMS) {
    if (hindi.includes(term)) {
      found.add(term);
    }
  }
  return [...found];
}

function textFields(content: ExplainContent): Array<[string, string]> {
  const fields: Array<[string, string]> = [
    ["explanation.en", content.explanation.en],
    ["explanation.hi", content.explanation.hi],
  ];
  content.recommended_checks.forEach((check, i) => {
    fields.push([`recommended_checks[${i}].en`, check.en], [`recommended_checks[${i}].hi`, check.hi]);
  });
  return fields;
}

/** Run the blocklist and number checks over every text field. */
export function checkNeutrality(content: ExplainContent, payload: ExplainRequest): GuardResult {
  const allowed = allowedNumbers(payload);
  const violations: string[] = [];
  for (const [field, text] of textFields(content)) {
    for (const term of findBlockedTerms(text)) {
      violations.push(`blocked term "${term}" in ${field}`);
    }
    for (const raw of findUnsupportedNumbers(text, allowed)) {
      violations.push(`number "${raw}" in ${field} does not match any value in the data`);
    }
    if (field.endsWith(".hi") && !DEVANAGARI.test(text)) {
      violations.push(`${field} is not written in Hindi (Devanagari)`);
    }
  }
  return { passed: violations.length === 0, violations };
}

/** Check one free-text string against the blocklist and the payload numbers. */
export function checkText(text: string, payload: ExplainRequest): GuardResult {
  const violations = [
    ...findBlockedTerms(text).map((t) => `blocked term "${t}"`),
    ...findUnsupportedNumbers(text, allowedNumbers(payload)).map(
      (n) => `number "${n}" does not match any value in the data`,
    ),
  ];
  return { passed: violations.length === 0, violations };
}
