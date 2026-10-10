import { describe, expect, it } from "vitest";
import { formatMetricValue } from "./format";

describe("formatMetricValue", () => {
  it("shows rates and shares as percentages", () => {
    expect(formatMetricValue("deletion_rate", 0.2203)).toBe("22.0%");
    expect(formatMetricValue("reason_share", 0.8218)).toBe("82.2%");
    expect(formatMetricValue("f_removed_share", 0.7126)).toBe("71.3%");
    expect(formatMetricValue("house_cluster_share", 0.38)).toBe("38.0%");
  });

  it("shows counts as plain numbers, not percentages", () => {
    expect(formatMetricValue("dq_count", 7)).toBe("7");
    expect(formatMetricValue("duplicate_pairs", 13)).toBe("13");
    expect(formatMetricValue("dead_under_40", 31)).toBe("31");
    expect(formatMetricValue("max_house_additions", 45)).toBe("45");
    expect(formatMetricValue("duplicate_pairs", 1.5)).toBe("1.5");
  });
});
