"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders assistant chat content as markdown. User bubbles stay plain text.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="iv-md">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
