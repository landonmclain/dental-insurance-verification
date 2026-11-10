import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import VerificationDemo from "./VerificationDemo";

// A minimal SSE stream reader that yields the given frames.
function makeStream(frames: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const chunks = frames.map((f) => encoder.encode(f));
  return new ReadableStream({
    start(controller) {
      chunks.forEach((c) => controller.enqueue(c));
      controller.close();
    },
  });
}

const sampleCards = [
  { id: "card_0000", payer: "BrightSmile Dental", image_url: "/cards/card_0000/image" },
];

const resultSummary = {
  patient_name: "Jane Doe",
  payer: "BrightSmile Dental",
  eligibility_status: "active",
  coverage_type: "Dental",
  benefits: [{ name: "Cleanings", value: "2 per year" }],
  missing: [],
  headline: "Jane Doe is ACTIVE with dental coverage.",
};

function sseFrame(step: string, detail = "") {
  return `data: ${JSON.stringify({ step, status: "done", detail, elapsed_ms: 1 })}\n\n`;
}

// Route the demo's fetch calls: card list, verify (job id), SSE stream.
function mockFetch({ verifyOk = true }: { verifyOk?: boolean } = {}) {
  return vi.fn((url: string) => {
    if (url === "/api/cards") {
      return Promise.resolve({ ok: true, json: async () => sampleCards });
    }
    if (url === "/api/verify") {
      return Promise.resolve({ ok: verifyOk, json: async () => ({ job_id: "job-1" }) });
    }
    return Promise.resolve({
      body: makeStream([
        sseFrame("extract"),
        sseFrame("result", JSON.stringify(resultSummary)),
        sseFrame("end"),
      ]),
    });
  });
}

async function submitCard() {
  fireEvent.click(screen.getByRole("button", { name: "Choose a sample card" }));
  await screen.findByText("BrightSmile Dental");
  fireEvent.click(screen.getByText("BrightSmile Dental"));
  fireEvent.click(screen.getByText("Send for verification"));
}

describe("VerificationDemo", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the benefit summary when a result event arrives", async () => {
    vi.stubGlobal("fetch", mockFetch());

    render(<VerificationDemo />);

    // Pick a sample card, then submit. The pipeline runs only on submit.
    await submitCard();

    // The result event must render the benefit summary.
    await waitFor(() => {
      expect(screen.getByText("Benefit summary")).toBeInTheDocument();
    });
    expect(screen.getByText("Cleanings")).toBeInTheDocument();
  });

  it("shows an error when the verify request fails", async () => {
    vi.stubGlobal("fetch", mockFetch({ verifyOk: false }));

    render(<VerificationDemo />);

    await submitCard();

    await waitFor(() => {
      expect(screen.getByText("Verification failed")).toBeInTheDocument();
    });
  });
});
