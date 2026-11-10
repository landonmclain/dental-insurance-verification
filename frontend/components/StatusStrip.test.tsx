import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusStrip } from "./StatusStrip";
import type { PipelineEvent } from "./VerificationDemo";

const doneEvents: PipelineEvent[] = [
  { step: "extract", status: "done", detail: "tier=ocr confidence=0.99", elapsed_ms: 10 },
  { step: "validate", status: "done", detail: "Fields OK", elapsed_ms: 20 },
  { step: "270", status: "done", detail: "payer=BSM001", elapsed_ms: 30 },
  { step: "eligibility", status: "done", detail: "status=active", elapsed_ms: 40 },
  { step: "summarize", status: "done", detail: "Summary ready", elapsed_ms: 50 },
  { step: "done", status: "done", detail: "Verification complete", elapsed_ms: 60 },
];

describe("StatusStrip", () => {
  it("renders all six step labels", () => {
    render(<StatusStrip events={[]} running={false} />);
    expect(screen.getByText("Reading card")).toBeInTheDocument();
    expect(screen.getByText("Validating fields")).toBeInTheDocument();
    expect(screen.getByText("Building eligibility request")).toBeInTheDocument();
    expect(screen.getByText("Sending for verification")).toBeInTheDocument();
    expect(screen.getByText("Writing benefit summary")).toBeInTheDocument();
    expect(screen.getByText("Complete")).toBeInTheDocument();
  });

  it("shows checkmarks for completed steps", () => {
    render(<StatusStrip events={doneEvents} running={false} />);
    // All six steps are done -> six checkmark circles.
    expect(screen.getAllByTestId("step-check")).toHaveLength(6);
  });

  it("renders the detail text of a done step", () => {
    render(<StatusStrip events={doneEvents} running={false} />);
    expect(screen.getByText("status=active")).toBeInTheDocument();
  });

  it("shows no checkmarks before any step completes", () => {
    render(<StatusStrip events={[]} running={false} />);
    expect(screen.queryByTestId("step-check")).not.toBeInTheDocument();
  });
});
