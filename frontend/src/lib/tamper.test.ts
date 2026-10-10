import { describe, expect, it } from "vitest";
import { tamperText } from "./tamper";

function diffCount(a: string, b: string): number {
  let n = Math.abs(a.length - b.length);
  for (let i = 0; i < Math.min(a.length, b.length); i += 1) if (a[i] !== b[i]) n += 1;
  return n;
}

describe("tamperText", () => {
  it("changes exactly one digit of the first number outside strings and keeps valid JSON", () => {
    const text = '{"ac_name":"Demo 999","ac_no":999,"removed":182}';
    const out = tamperText(text);
    expect(out.kind).toBe("digit");
    expect(out.text).toBe('{"ac_name":"Demo 999","ac_no":990,"removed":182}');
    expect(out.text.length).toBe(text.length);
    expect(diffCount(text, out.text)).toBe(1);
    expect(() => JSON.parse(out.text)).not.toThrow();
    expect({ before: out.before, after: out.after, index: out.index }).toEqual({
      before: "9",
      after: "0",
      index: text.indexOf('"ac_no":999') + '"ac_no":99'.length,
    });
  });

  it("skips digits inside strings, including escaped quotes", () => {
    const out = tamperText('{"id":"VG-2026-0001","note":"say \\"12\\"","n":5}');
    expect(out.text.endsWith('"n":6}')).toBe(true);
  });

  it("appends a single space when there is no number", () => {
    const out = tamperText('{"a":"b"}');
    expect(out).toMatchObject({ kind: "space", text: '{"a":"b"} ' });
  });
});
