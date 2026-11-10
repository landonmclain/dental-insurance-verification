"use client";

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
  prior_auth?: string;
};

type Coverage = "covered" | "not_covered" | "assumed" | "unknown";

export function coverageOf(line: BenefitLine): Coverage {
  if (line.non_covered) return "not_covered";
  if (line.status === "ACTIVE_COVERAGE") return "covered";
  // Coverage evidence: copay/coinsurance counts even when the payer reports it
  // with no per-code status (BCBS, Ameritas).
  if (line.coinsurance || line.copay) return "covered";
  if (line.limitations.length > 0) return "assumed";
  return "unknown";
}

const BADGE: Record<Coverage, { label: string; cls: string }> = {
  covered: { label: "Covered", cls: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400" },
  assumed: { label: "Covered (assumed)", cls: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400" },
  not_covered: { label: "Not covered", cls: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400" },
  unknown: { label: "Unknown", cls: "bg-slate-100 text-slate-500 dark:bg-neutral-800 dark:text-neutral-400" },
};

function prettyJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

// Coinsurance comes back as a fraction (0.1 = 10%); render as a percent.
function pct(value?: string): string | undefined {
  if (!value) return undefined;
  const f = parseFloat(value);
  if (Number.isNaN(f)) return value;
  if (f > 0 && f <= 1) return `${Math.round(f * 100)}%`;
  return `${Math.round(f)}%`;
}

const KIND_LABEL: Record<BenefitLimit["kind"], string> = {
  dollar: "Limit",
  visits: "Visits",
  codes: "Codes",
  note: "Note",
};

function kindLabel(kind: BenefitLimit["kind"]): string {
  return KIND_LABEL[kind];
}

export function BenefitsPanel({
  raw,
  x12,
  lines = [],
}: {
  raw: string;
  x12?: string;
  lines?: BenefitLine[];
}) {
  // Show only codes the 271 determines; "unknown" is noise.
  const known = lines.filter((l) => coverageOf(l) !== "unknown");
  const covered = known.filter((l) => coverageOf(l) === "covered").length;
  const assumed = known.filter((l) => coverageOf(l) === "assumed").length;
  const notCovered = known.length - covered - assumed;

  return (
    <div className="mt-8 space-y-4">
      <div className="rounded-xl border bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Benefit coverage</h2>
          <div className="flex gap-3 text-xs text-slate-500 dark:text-neutral-400">
            <span>
              <span className="font-medium text-green-600 dark:text-green-400">{covered}</span> covered
            </span>
            {assumed > 0 && (
              <span>
                <span className="font-medium text-amber-600 dark:text-amber-400">{assumed}</span> assumed
              </span>
            )}
            <span>
              <span className="font-medium text-red-600 dark:text-red-400">{notCovered}</span> not covered
            </span>
          </div>
        </div>

        <ul className="mt-4 divide-y dark:divide-neutral-800">
          {known.map((b) => {
            const cov = coverageOf(b);
            const badge = BADGE[cov];
            return (
              <li key={b.code}>
                <details className="group">
                  <summary className="flex cursor-pointer items-center gap-3 py-2 text-sm">
                    <svg
                      className="h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform group-open:rotate-90 dark:text-neutral-500"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className="w-20 shrink-0 font-mono font-medium">
                      {b.code || "(no code)"}
                    </span>
                    <span className="flex-1 text-slate-600 dark:text-neutral-300">
                      {b.description || b.category || "—"}
                    </span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${badge.cls}`}
                    >
                      {badge.label}
                    </span>
                  </summary>
                  <div className="pb-2 pl-4 text-xs text-slate-500 dark:text-neutral-400">
                    {b.category && <div>Category: {b.category}</div>}
                    {b.copay && <div>Copay: {b.copay}</div>}
                    {b.coinsurance && <div>Coinsurance: {pct(b.coinsurance)}</div>}
                    {b.deductible && <div>Deductible: {b.deductible}</div>}
                    {b.out_of_pocket && <div>Out-of-pocket: {b.out_of_pocket}</div>}
                    {b.prior_auth && <div>Prior auth: {b.prior_auth}</div>}
                    {b.limitations.length > 0 && (
                      <div className="mt-1 space-y-1">
                        {b.limitations.map((lim, i) => (
                          <div key={i} className="flex items-baseline gap-2">
                            <span className="w-14 shrink-0 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-neutral-500">
                              {kindLabel(lim.kind)}
                            </span>
                            <span className="text-slate-600 dark:text-neutral-300">{lim.text}</span>
                            {lim.codes.length > 0 && (
                              <span className="font-mono text-slate-400 dark:text-neutral-500">
                                {lim.codes.join(" ")}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {b.system && <div>System: {b.system}</div>}
                  </div>
                </details>
              </li>
            );
          })}
        </ul>
        {known.length === 0 && (
          <p className="mt-4 text-sm text-slate-500 dark:text-neutral-400">
            This payer doesn't report per-code coverage.
          </p>
        )}
        {assumed > 0 && (
          <p className="mt-4 text-xs text-slate-400 dark:text-neutral-500">
            "Covered (assumed)" means this payer reports coverage at the plan
            level only; per-code coverage is inferred from the plan's limits.
          </p>
        )}
      </div>

      {x12 && (
        <details className="rounded-xl border bg-neutral-950 p-4 dark:border-neutral-800">
          <summary className="cursor-pointer text-sm font-semibold text-neutral-300">
            Raw X12 271 (EDI)
          </summary>
          <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-neutral-200">
            {x12}
          </pre>
        </details>
      )}

      <details className="rounded-xl border bg-neutral-950 p-4 dark:border-neutral-800">
        <summary className="cursor-pointer text-sm font-semibold text-neutral-300">
          Raw 271 response
        </summary>
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-neutral-200">
          {prettyJson(raw)}
        </pre>
      </details>
    </div>
  );
}
