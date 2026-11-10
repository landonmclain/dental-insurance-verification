"use client";

import { useEffect, useRef, useState } from "react";
import { Markdown } from "./Markdown";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

const SUGGESTIONS = [
  "Is a crown covered?",
  "What's the deductible?",
  "Summarize this patient's benefits",
];

export function AskDrawer({
  open,
  onClose,
  runKey,
  scopeLabel,
  raw271,
  payerName,
  card,
}: {
  open: boolean;
  onClose: () => void;
  runKey: string;
  scopeLabel?: string;
  raw271?: string;
  payerName?: string;
  card?: Record<string, unknown>;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Reset the thread when the run changes; closing/reopening keeps history.
  useEffect(() => {
    setMessages([]);
    setInput("");
    setThinking(false);
  }, [runKey]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, thinking]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || thinking) return;
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setThinking(true);

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          history,
          raw_271: raw271,
          payer_name: payerName,
          card,
        }),
      });
      if (!res.ok || !res.body) throw new Error("Ask failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let answer = "";

      setMessages((m) => [...m, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame.trim();
          if (!line.startsWith("data: ")) continue;
          const ev = JSON.parse(line.slice(6));
          if (ev.type === "token") {
            answer += ev.content;
            setMessages((m) => {
              const next = [...m];
              next[next.length - 1] = { role: "assistant", content: answer };
              return next;
            });
          } else if (ev.type === "error") {
            setMessages((m) => {
              const next = [...m];
              next[next.length - 1] = {
                role: "assistant",
                content: `⚠️ ${ev.message}`,
              };
              return next;
            });
          }
        }
      }
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `⚠️ ${e instanceof Error ? e.message : "Something went wrong"}`,
        },
      ]);
    } finally {
      setThinking(false);
    }
  }

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-neutral-900/40 dark:bg-neutral-950/60"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col bg-white shadow-xl transition-transform duration-300 dark:bg-neutral-900 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        aria-label="Ask about this patient's benefits"
      >
        <header className="flex items-center justify-between border-b px-5 py-4 dark:border-neutral-800">
          <div>
            <h2 className="text-base font-semibold">
              Ask about this patient's benefits
            </h2>
            <p className="text-xs text-slate-400 dark:text-neutral-500">
              Scoped to {scopeLabel || "this card run"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-neutral-500 dark:hover:bg-neutral-800 dark:hover:text-neutral-300"
            aria-label="Close"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </header>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          {messages.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-neutral-400">
              Ask a question about this patient's benefits. Answers come only
              from the verified data for this card.
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-800 dark:bg-neutral-800 dark:text-neutral-200"
                }`}
              >
                {m.role === "user" ? (
                  <span className="whitespace-pre-wrap">{m.content}</span>
                ) : (
                  <Markdown>{m.content}</Markdown>
                )}
              </div>
            </div>
          ))}
          {thinking && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-400 dark:bg-neutral-800 dark:text-neutral-500">
                <span className="inline-flex gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 dark:bg-neutral-500" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:0.1s] dark:bg-neutral-500" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:0.2s] dark:bg-neutral-500" />
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="border-t px-5 py-4 dark:border-neutral-800">
          {messages.length === 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:border-blue-300 hover:text-blue-600 dark:border-neutral-700 dark:text-neutral-400 dark:hover:border-blue-500 dark:hover:text-blue-400"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about this patient's benefits…"
              // text-base (16px): iOS Safari zooms inputs under 16px.
              className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-base focus:border-blue-400 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
            />
            <button
              type="submit"
              disabled={!input.trim() || thinking}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
            >
              Send
            </button>
          </form>
        </div>
      </aside>
    </>
  );
}
