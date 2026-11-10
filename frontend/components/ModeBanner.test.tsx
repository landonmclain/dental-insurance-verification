import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ModeBanner } from "./ModeBanner";

function mockConfig(config: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve(config) })
    )
  );
}

describe("ModeBanner", () => {
  it("shows the mock tier with no model chips and chat off", async () => {
    mockConfig({
      mode: "mock",
      ask_enabled: false,
      vision_model: "",
      vision_provider: "Local",
      ask_model: "",
      ask_provider: "Local",
      stedi_key_set: false,
    });
    render(<ModeBanner />);
    await waitFor(() => expect(screen.getByText("MOCK MODE")).toBeInTheDocument());
    expect(screen.getByText(/No API keys, no model calls/)).toBeInTheDocument();
    expect(screen.queryByText(/vision:/)).not.toBeInTheDocument();
    expect(screen.getByText(/Q&A chat: off/)).toBeInTheDocument();
    expect(screen.queryByText(/Stedi key:/)).not.toBeInTheDocument();
  });

  it("shows the llm tier with the active models, no Stedi chip", async () => {
    mockConfig({
      mode: "llm",
      ask_enabled: true,
      vision_model: "openrouter:deepseek/deepseek-v4.1-flash",
      vision_provider: "OpenRouter",
      ask_model: "openrouter:deepseek/deepseek-v4.1-flash",
      ask_provider: "OpenRouter",
      stedi_key_set: false,
    });
    render(<ModeBanner />);
    await waitFor(() => expect(screen.getByText("LLM MODE")).toBeInTheDocument());
    expect(
      screen.getByText(/vision: openrouter:deepseek\/deepseek-v4\.1-flash/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/q\/a: openrouter:deepseek\/deepseek-v4\.1-flash/)
    ).toBeInTheDocument();
    expect(screen.getByText(/Q&A chat: on/)).toBeInTheDocument();
    expect(screen.queryByText(/Stedi key:/)).not.toBeInTheDocument();
  });

  it("shows the live tier with local models and Stedi set", async () => {
    mockConfig({
      mode: "live",
      ask_enabled: true,
      vision_model: "local:swift-1.5-iq2_xs",
      vision_provider: "Local",
      ask_model: "local:swift-1.5-iq2_xs",
      ask_provider: "Local",
      stedi_key_set: true,
    });
    render(<ModeBanner />);
    await waitFor(() => expect(screen.getByText("LIVE MODE")).toBeInTheDocument());
    expect(screen.getByText(/vision: local:swift-1\.5-iq2_xs/)).toBeInTheDocument();
    expect(screen.getByText(/q\/a: local:swift-1\.5-iq2_xs/)).toBeInTheDocument();
    expect(screen.getByText(/Stedi key: set/)).toBeInTheDocument();
    expect(screen.getByText(/Q&A chat: on/)).toBeInTheDocument();
  });
});
