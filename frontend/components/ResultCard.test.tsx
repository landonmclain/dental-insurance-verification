import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResultCard } from "./ResultCard";
import type { BenefitSummary } from "./VerificationDemo";

const activeSummary: BenefitSummary = {
  patient_name: "Jane Doe",
  payer: "BrightSmile Dental",
  eligibility_status: "active",
  coverage_type: "Dental",
  benefits: [
    { name: "Cleanings", value: "2 per year" },
    { name: "Preventive coverage", value: "100%" },
  ],
  missing: ["Waiting periods"],
  headline: "Jane Doe is ACTIVE with dental coverage.",
};

describe("ResultCard", () => {
  it("shows ACTIVE badge for active status", () => {
    render(<ResultCard summary={activeSummary} />);
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });

  it("renders each benefit with its value", () => {
    render(<ResultCard summary={activeSummary} />);
    expect(screen.getByText("Cleanings")).toBeInTheDocument();
    expect(screen.getByText("2 per year")).toBeInTheDocument();
    expect(screen.getByText("Preventive coverage")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("flags missing items for confirmation", () => {
    render(<ResultCard summary={activeSummary} />);
    expect(screen.getByText("Confirm with payer:")).toBeInTheDocument();
    expect(screen.getByText("Waiting periods")).toBeInTheDocument();
  });

  it("shows INACTIVE badge for inactive status", () => {
    const inactive = { ...activeSummary, eligibility_status: "inactive" };
    render(<ResultCard summary={inactive} />);
    expect(screen.getByText("INACTIVE")).toBeInTheDocument();
  });
});
