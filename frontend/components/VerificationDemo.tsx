"use client";

import { useEffect, useState } from "react";
import { VerificationForm } from "./VerificationForm";
import { StatusStrip } from "./StatusStrip";
import { ExtractionPanel } from "./ExtractionPanel";
import { ResultCard } from "./ResultCard";
import { BenefitsPanel } from "./BenefitsPanel";
import { AskDrawer } from "./AskDrawer";
import { ModeBanner } from "./ModeBanner";

export type PipelineEvent = {
  step: string;
  status: string;
  detail: string;
  elapsed_ms: number;
};

export type BenefitSummary = {
  patient_name?: string;
  payer?: string;
  eligibility_status: string;
  coverage_type?: string;
  benefits: { name: string; value?: string; needs_confirmation?: boolean }[];
  benefit_lines: BenefitLine[];
  non_covered: { name: string; value?: string }[];
  missing: string[];
  headline: string;
  raw_response?: string;
  x12?: string;
};

export type BenefitLimit = {
  kind: "dollar" | "visits" | "codes" | "note";
  text: string;
  codes: string[];
};

export type BenefitLine = {
  code: string;
  system?: string;
  description?: string;
  category?: string;
  status?: string;
  coverage_level?: string;
  copay?: string;
  coinsurance?: string;
  deductible?: string;
  out_of_pocket?: string;
  limitations: BenefitLimit[];
  non_covered: boolean;
};

export type ExtractionResult = {
  card: {
    member_id: string;
    group_id?: string;
    payer_id?: string;
    subscriber_first?: string;
    subscriber_last?: string;
    subscriber_dob?: string;
    payer_name?: string;
    plan_name?: string;
    subscriber_address_line1?: string;
    subscriber_address_city?: string;
    subscriber_address_state?: string;
    subscriber_address_zip?: string;
  };
  confidences: Record<string, number>;
  overall_confidence: number;
  tier: string;
  needs_review: boolean;
  raw_text?: string;
};

export default function VerificationDemo() {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [summary, setSummary] = useState<BenefitSummary | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [askOpen, setAskOpen] = useState(false);
  const [runId, setRunId] = useState(0);
  // Server-driven feature flags: the ask chat is not available in mock mode.
  const [askEnabled, setAskEnabled] = useState(true);

  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then((c) => setAskEnabled(Boolean(c.ask_enabled)))
      .catch(() => setAskEnabled(false));
  }, []);

  async function handleSubmit(cardId: string) {
    setRunning(true);
    setEvents([]);
    setSummary(null);
    setExtraction(null);
    setError(null);
    setAskOpen(false);
    setRunId((n) => n + 1);

    try {
      // 1. Start the pipeline on the chosen sample card, get a job id.
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: cardId }),
      });
      if (!res.ok) throw new Error("Verification failed");
      const { job_id } = await res.json();
      console.log("[verify] POST /api/verify ->", res.status, { card_id: cardId, job_id });

      // 2. Subscribe to the SSE event stream and render each event truthfully.
      console.log("[verify] opening SSE stream for job", job_id);
      const stream = await fetch(`/api/events/${job_id}`);
      const reader = stream.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame.trim();
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6)) as PipelineEvent;
          console.log(
            "[event]",
            event.step,
            event.status,
            `${event.elapsed_ms}ms`,
            event.detail
          );
          setEvents((prev) => [...prev, event]);
          if (event.step === "error") {
            setError(event.detail);
            setRunning(false);
            return;
          }
          if (event.step === "result") {
            setSummary(JSON.parse(event.detail) as BenefitSummary);
          }
          if (event.step === "extract_result") {
            setExtraction(JSON.parse(event.detail) as ExtractionResult);
          }
          if (event.step === "end") {
            setRunning(false);
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6">
        <ModeBanner />
      </div>
      <div className="grid gap-8 lg:grid-cols-2">
        <VerificationForm onSubmit={handleSubmit} disabled={running} />
        <div className="space-y-6">
          <StatusStrip events={events} running={running} />
          {extraction && <ExtractionPanel result={extraction} />}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              {error}
            </div>
          )}
        </div>
      </div>
      {summary && askEnabled && (
        <div className="mt-8 flex justify-end">
          <button
            onClick={() => setAskOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400 dark:hover:bg-blue-900"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M10 2c-4.42 0-8 3.36-8 7.5 0 1.5.47 2.9 1.28 4.07L2 18l4.6-1.2A8.1 8.1 0 0010 17c4.42 0 8-3.36 8-7.5S14.42 2 10 2zm-3 8a1 1 0 100-2 1 1 0 000 2zm3 0a1 1 0 100-2 1 1 0 000 2zm3 0a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
            Ask about this patient's benefits
          </button>
        </div>
      )}
      {summary?.coverage_type === "Medical" && (
        <div className="mt-8 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300">
          <strong>⚠️ This appears to be a medical card, not dental.</strong>{" "}
          Please choose a dental card to verify dental benefits.
        </div>
      )}
      {summary && <ResultCard summary={summary} raw={summary.raw_response} />}
      {summary?.raw_response && (
        <BenefitsPanel
          raw={summary.raw_response}
          x12={summary.x12}
          lines={summary.benefit_lines}
          nonCovered={summary.non_covered}
        />
      )}
      {askEnabled && (
        <AskDrawer
          open={askOpen}
          onClose={() => setAskOpen(false)}
          runKey={String(runId)}
          scopeLabel={extraction?.card.payer_name}
          payerName={extraction?.card.payer_name}
          card={extraction?.card}
          raw271={summary?.raw_response}
        />
      )}
    </div>
  );
}
