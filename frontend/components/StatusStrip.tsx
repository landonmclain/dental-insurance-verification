"use client";

import type { PipelineEvent } from "./VerificationDemo";

const STEP_LABELS: Record<string, string> = {
  extract: "Reading card",
  validate: "Validating fields",
  "270": "Building eligibility request",
  eligibility: "Sending for verification",
  summarize: "Writing benefit summary",
  done: "Complete",
};

const STEPS = ["extract", "validate", "270", "eligibility", "summarize", "done"];

type Props = {
  events: PipelineEvent[];
  running: boolean;
};

export function StatusStrip({ events, running }: Props) {
  return (
    <div className="rounded-xl border bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <h2 className="mb-4 text-lg font-semibold">Verification status</h2>
      <ol className="space-y-3">
        {STEPS.map((step) => {
          const ev = events.find((e) => e.step === step && e.status === "done");
          const started = events.some((e) => e.step === step && e.status === "started");
          const isActive = running && started && !ev;
          return (
            <li key={step} className="flex items-center gap-3 text-sm">
              {isActive ? (
                <span className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
              ) : ev ? (
                <span
                  data-testid="step-check"
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-600"
                >
                  <svg
                    className="h-3 w-3 text-white"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 111.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </span>
              ) : (
                <span className="h-5 w-5 shrink-0 rounded-full border-2 border-slate-200 dark:border-neutral-700" />
              )}
              <span
                className={
                  ev
                    ? "text-slate-900 dark:text-neutral-100"
                    : isActive
                    ? "font-medium text-blue-600 dark:text-blue-400"
                    : "text-slate-400 dark:text-neutral-500"
                }
              >
                {STEP_LABELS[step] ?? step}
              </span>
              {ev?.detail && <span className="ml-auto text-xs text-slate-400 dark:text-neutral-500">{ev.detail}</span>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
