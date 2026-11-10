"use client";

import { useEffect, useState } from "react";

export type ModeConfig = {
  mode: string;
  ask_enabled: boolean;
  vision_model: string;
  vision_provider: string;
  ask_model: string;
  ask_provider: string;
  stedi_key_set: boolean;
};

const BANNER: Record<string, { label: string; lead: string; tone: string }> = {
  mock: {
    label: "MOCK",
    lead: "No API keys, no model calls. The vision model is not invoked; answers come from the card's ground truth.",
    tone: "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300",
  },
  llm: {
    label: "LLM",
    lead: "Real vision and text models, and a deterministic mock eligibility call (no Stedi key).",
    tone: "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300",
  },
  live: {
    label: "LIVE",
    lead: "Real vision and text models, and a real eligibility call to Stedi.",
    tone: "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  },
};

export function ModeBanner() {
  const [config, setConfig] = useState<ModeConfig | null>(null);

  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then(setConfig)
      .catch(() => setConfig(null));
  }, []);

  if (!config) return null;
  const banner = BANNER[config.mode] ?? BANNER.mock;
  const hasModels = config.mode !== "mock";

  return (
    <div
      className={`rounded-lg border px-4 py-3 text-sm ${banner.tone}`}
      data-mode={config.mode}
    >
      <span className="font-semibold tracking-wide">{banner.label} MODE</span>
      <span className="mx-2">—</span>
      <span>{banner.lead}</span>
      <div className="mt-2 flex flex-wrap gap-2 text-xs opacity-80">
        {hasModels && (
          <span className="rounded px-2 py-0.5 border" data-key="vision">
            vision: {config.vision_model}
          </span>
        )}
        {hasModels && config.ask_enabled && (
          <span className="rounded px-2 py-0.5 border" data-key="askmodel">
            q/a: {config.ask_model}
          </span>
        )}
        {config.mode === "live" && (
          <span className="rounded px-2 py-0.5 border" data-key="stedi">
            Stedi key: {config.stedi_key_set ? "set" : "not set"}
          </span>
        )}
        <span className="rounded px-2 py-0.5 border" data-key="ask">
          Q&amp;A chat: {config.ask_enabled ? "on" : "off"}
        </span>
      </div>
    </div>
  );
}
