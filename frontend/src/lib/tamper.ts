/** Tamper simulation: change exactly one character so the file's hash no longer matches. */

export interface TamperResult {
  text: string;
  /** Index of the changed character (or of the appended space). */
  index: number;
  before: string;
  after: string;
  /** "digit" when a number was changed, "space" when a space was appended. */
  kind: "digit" | "space";
}

/**
 * Find the first number outside a JSON string and change its LAST digit
 * (changing the last digit keeps the JSON valid and the length unchanged).
 * If the text has no number outside strings, append a single space.
 */
export function tamperText(text: string): TamperResult {
  let inString = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inString) {
      if (ch === "\\") i += 1; // skip the escaped character
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') {
      inString = true;
      continue;
    }
    if (ch !== undefined && ch >= "0" && ch <= "9") {
      let end = i;
      while (end + 1 < text.length && /[0-9]/.test(text[end + 1] ?? "")) end += 1;
      const before = text[end] ?? "0";
      const after = before === "9" ? "0" : String(Number(before) + 1);
      return { text: text.slice(0, end) + after + text.slice(end + 1), index: end, before, after, kind: "digit" };
    }
  }
  return { text: `${text} `, index: text.length, before: "", after: " ", kind: "space" };
}
