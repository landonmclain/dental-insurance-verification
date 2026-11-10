import { describe, expect, it } from "vitest";
import { coverageOf, type BenefitLine } from "./BenefitsPanel";

function line(overrides: Partial<BenefitLine>): BenefitLine {
  return {
    code: "D0120",
    limitations: [],
    non_covered: false,
    ...overrides,
  };
}

describe("coverageOf", () => {
  it("marks ACTIVE_COVERAGE as covered", () => {
    expect(coverageOf(line({ status: "ACTIVE_COVERAGE" }))).toBe("covered");
  });

  it("marks non_covered as not covered even with a status", () => {
    expect(
      coverageOf(line({ status: "ACTIVE_COVERAGE", non_covered: true }))
    ).toBe("not_covered");
  });

  it("marks a line with no status and not non-covered as unknown", () => {
    expect(coverageOf(line({}))).toBe("unknown");
  });

  it("marks a non-ACTIVE status as unknown", () => {
    expect(coverageOf(line({ status: "INACTIVE" }))).toBe("unknown");
  });

  it("marks a line with coinsurance as covered even without a status", () => {
    expect(coverageOf(line({ coinsurance: "0.5" }))).toBe("covered");
  });

  it("marks a line with copay as covered even without a status", () => {
    expect(coverageOf(line({ copay: "25" }))).toBe("covered");
  });

  it("marks a line with a limitation as assumed covered even without a status", () => {
    expect(
      coverageOf(line({ limitations: [{ kind: "visits", text: "2 visits", codes: [] }] }))
    ).toBe("assumed");
  });
});
