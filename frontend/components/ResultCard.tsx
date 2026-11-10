"use client";

import type { BenefitSummary } from "./VerificationDemo";
import { parsePayerProvider } from "./PayerProviderPanel";

export function ResultCard({
  summary,
  raw,
}: {
  summary: BenefitSummary;
  raw?: string;
}) {
  const active = summary.eligibility_status === "active";
  const { subscriber, payer, provider } = parsePayerProvider(raw ?? "");

  return (
    <div className="mt-8 rounded-xl border bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Benefit summary</h2>
        <span
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            active ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400" : "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400"
          }`}
        >
          {active ? "ACTIVE" : summary.eligibility_status.toUpperCase()}
        </span>
      </div>

      {/* Subscriber, Payer, Provider — in that order */}
      <div className="mb-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-neutral-500">
            Subscriber
          </h3>
          <p className="text-sm font-medium text-slate-900 dark:text-neutral-100">{subscriber.name}</p>
          <div className="mt-0.5 space-y-0.5 text-xs text-slate-500 dark:text-neutral-400">
            {subscriber.memberId && <p>Member ID: {subscriber.memberId}</p>}
            {subscriber.dateOfBirth && <p>DOB: {subscriber.dateOfBirth}</p>}
            {subscriber.gender && <p>Gender: {subscriber.gender}</p>}
            {subscriber.address?.line1 && (
              <p>
                {subscriber.address.line1}, {subscriber.address.city},{" "}
                {subscriber.address.state} {subscriber.address.postalCode}
              </p>
            )}
            {subscriber.planStart && (
              <p>
                Plan: {subscriber.planStart}
                {subscriber.planEnd ? ` – ${subscriber.planEnd}` : ""}
              </p>
            )}
            {subscriber.groupName && (
              <p>
                Group: {subscriber.groupName}
                {subscriber.groupNumber ? ` (${subscriber.groupNumber})` : ""}
              </p>
            )}
            {subscriber.planNetworkName && (
              <p>
                Network: {subscriber.planNetworkName}
                {subscriber.planNetworkNumber ? ` (${subscriber.planNetworkNumber})` : ""}
              </p>
            )}
          </div>
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-neutral-500">
            Payer
          </h3>
          <p className="text-sm font-medium text-slate-900 dark:text-neutral-100">{payer.name}</p>
          <div className="mt-0.5 space-y-0.5 text-xs text-slate-500 dark:text-neutral-400">
            {payer.id && <p>ID: {payer.id}</p>}
            {payer.tin && <p>TIN: {payer.tin}</p>}
          </div>
          {payer.contacts?.length ? (
            <ul className="mt-2 space-y-2 text-xs text-slate-500">
              {payer.contacts.map((c, i) => (
                <li key={i}>
                  {c.name && <div className="font-medium text-slate-600 dark:text-neutral-300">{c.name}</div>}
                  {c.phoneNumbers?.map((ph, j) => <div key={j}>{ph}</div>)}
                  {c.urls?.map((u, j) => <div key={j}>{u}</div>)}
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-neutral-500">
            Provider
          </h3>
          <p className="text-sm font-medium text-slate-900 dark:text-neutral-100">{provider.name}</p>
          <div className="mt-0.5 space-y-0.5 text-xs text-slate-500 dark:text-neutral-400">
            {provider.npi && <p>NPI: {provider.npi}</p>}
            {provider.type && <p>Type: {provider.type}</p>}
          </div>
        </div>
      </div>

      <table className="w-full text-sm">
        <tbody>
          {summary.benefits.map((b) => (
            <tr key={b.name} className="border-b last:border-0 dark:border-neutral-800">
              <td className="py-2 pr-3 text-slate-700 dark:text-neutral-300">
                <div className="flex flex-wrap items-center gap-2">
                  <span>{b.name}</span>
                  {b.category && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-neutral-800 dark:text-neutral-300">
                      {b.category}
                    </span>
                  )}
                </div>
              </td>
              <td className="py-2 text-right font-medium text-slate-900 dark:text-neutral-100">
                {b.value ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {summary.missing.length > 0 && (
        <div className="mt-4 rounded-lg bg-amber-50 p-3 text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-400">
          <p className="mb-1 font-medium">Confirm with payer:</p>
          <ul className="list-inside list-disc">
            {summary.missing.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
