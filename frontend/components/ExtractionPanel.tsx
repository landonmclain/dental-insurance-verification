"use client";

import type { ExtractionResult } from "./VerificationDemo";

export function ExtractionPanel({ result }: { result: ExtractionResult }) {
  const fields: [string, string | undefined][] = [
    ["Member ID", result.card.member_id],
    ["Group ID", result.card.group_id],
    ["Payer ID", result.card.payer_id],
    ["Payer", result.card.payer_name],
    ["Plan", result.card.plan_name],
    [
      "Subscriber",
      [result.card.subscriber_first, result.card.subscriber_last]
        .filter(Boolean)
        .join(" ") || undefined,
    ],
    [
      "Address",
      [
        result.card.subscriber_address_line1,
        result.card.subscriber_address_city,
        result.card.subscriber_address_state,
        result.card.subscriber_address_zip,
      ]
        .filter(Boolean)
        .join(", ") || undefined,
    ],
  ].filter(([, v]) => v !== undefined && v !== "");

  return (
    <details className="rounded-xl border bg-neutral-950 p-4 dark:border-neutral-800">
      <summary className="cursor-pointer text-sm font-semibold text-neutral-300">
        Raw OCR / VLM output
      </summary>
      <div className="mt-3 space-y-3 text-xs text-neutral-200">
        <div className="flex gap-4">
          <span>
            tier: <span className="font-mono">{result.tier}</span>
          </span>
          <span>
            confidence:{" "}
            <span className="font-mono">{result.overall_confidence.toFixed(2)}</span>
          </span>
        </div>
        <table className="w-full text-left">
          <tbody>
            {fields.map(([label, value]) => (
              <tr key={label} className="border-b border-neutral-800 last:border-0">
                <td className="py-1 pr-3 text-neutral-400">{label}</td>
                <td className="py-1 font-mono">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {result.raw_text && (
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-neutral-300">
            {result.raw_text}
          </pre>
        )}
      </div>
    </details>
  );
}
