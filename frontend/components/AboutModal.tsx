"use client";

import { useState } from "react";

const STEPS = [
  {
    name: "Extract",
    detail:
      "OCR reads the card, then a vision model pulls the fields — member ID, subscriber name, payer, plan, group. Each field gets a confidence score; low-confidence results are flagged for human review.",
  },
  {
    name: "Validate",
    detail:
      "The extracted fields are checked against the payer's known formats (member ID, payer ID) before anything is sent out.",
  },
  {
    name: "270",
    detail:
      "The card data is assembled into an X12 270 eligibility request.",
  },
  {
    name: "Eligibility",
    detail:
      "The 270 is sent to the eligibility provider (Stedi) — the only external call in the pipeline. Stedi returns a 271 response.",
  },
  {
    name: "Summarize",
    detail:
      "The 271 is parsed into a benefit summary: deductible, coinsurance, per-code coverage, and limits.",
  },
  {
    name: "Ask",
    detail:
      "Once the summary is ready, you can ask questions about the results — e.g. \"Is a crown covered?\" — and get answers grounded only in this card's parsed benefits.",
  },
];

export function AboutModal() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:border-blue-300 hover:text-blue-600 dark:border-neutral-700 dark:text-neutral-400 dark:hover:border-blue-500 dark:hover:text-blue-400"
      >
        About
      </button>
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4 dark:bg-neutral-950/60"
          onClick={() => setOpen(false)}
        >
          <div
            className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl dark:bg-neutral-900"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold">
                  How this pipeline works
                </h2>
                <p className="text-sm text-slate-500 dark:text-neutral-400">
                  From card photo to verified benefit summary.
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-neutral-500 dark:hover:bg-neutral-800 dark:hover:text-neutral-300"
                aria-label="Close"
              >
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              </button>
            </div>

            <ol className="space-y-4">
              {STEPS.map((s, i) => (
                <li key={s.name} className="flex gap-3">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
                    {i + 1}
                  </div>
                  <div>
                    <p className="font-medium">{s.name}</p>
                    <p className="text-sm text-slate-600 dark:text-neutral-300">{s.detail}</p>
                  </div>
                </li>
              ))}
            </ol>

            <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
              <strong>Privacy:</strong> the cards are synthetic samples — no
              real patient info. But they are real images: each one is actually
              scanned, read by OCR and a vision model, and run through the full
              eligibility flow. In production this is meant to run locally,
              with the only external call being the eligibility API to Stedi.
            </div>
          </div>
        </div>
      )}
    </>
  );
}
