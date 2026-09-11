"use client";

import { useState } from "react";
import { Copy, RotateCcw } from "lucide-react";
import type { ChatCitation } from "@/lib/api";
import { CitationText } from "@/components/source-drawer";

/** رسالة المستخدم: فقاعة خفيفة محايدة، وزن 400، بلا ألوان صارخة. */
export function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-start">
      <div className="fade-in max-w-[85%] rounded-[20px] bg-[var(--user-message)] px-4 py-2.5">
        <p className="whitespace-pre-wrap text-[16px] font-normal leading-7 text-[var(--foreground)]">
          {content}
        </p>
      </div>
    </div>
  );
}

function MessageActions({
  content,
  onRetry,
}: {
  content: string;
  onRetry?: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // المتصفح قد يرفض الوصول للحافظة
    }
  };
  const buttonClass =
    "grid h-7 place-items-center rounded-lg px-1.5 text-[var(--muted-foreground)] transition-colors duration-150 hover:bg-[var(--surface)] hover:text-[var(--foreground)]";

  return (
    <div className="mt-1.5 flex items-center gap-0.5">
      <button onClick={() => void copy()} aria-label="نسخ" title="نسخ" className={buttonClass}>
        {copied ? (
          <span className="px-0.5 text-[11px] text-[var(--muted-foreground)]">تم النسخ</span>
        ) : (
          <Copy size={13} strokeWidth={1.7} />
        )}
      </button>
      {onRetry ? (
        <button onClick={onRetry} aria-label="إعادة المحاولة" title="إعادة المحاولة" className={buttonClass}>
          <RotateCcw size={13} strokeWidth={1.7} />
        </button>
      ) : null}
    </div>
  );
}

/** صف المصادر أسفل الإجابة: حتى 3 مرئية ثم +N. */
function SourcesRow({
  citations,
  onOpen,
}: {
  citations: ChatCitation[];
  onOpen: (index: number | null) => void;
}) {
  const visible = citations.slice(0, 3);
  const hidden = citations.length - visible.length;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5">
      <span className="text-[12px] text-[var(--muted-foreground)]">المصادر</span>
      {visible.map((citation) => (
        <button
          key={citation.index}
          onClick={() => onOpen(citation.index)}
          className="h-7 rounded-lg border border-[var(--border)] bg-[var(--background)] px-2.5 text-[11.5px] text-[var(--muted)] transition-colors duration-150 hover:border-[var(--border-strong)] hover:text-[var(--foreground)]"
        >
          [{citation.index}] {citation.title.split(" ")[0]}
          {citation.provider === "sistani" ? " · السيستاني" : citation.provider === "turath" ? " · تراث" : ""}
        </button>
      ))}
      {hidden > 0 ? (
        <button
          onClick={() => onOpen(null)}
          className="text-[11.5px] text-[var(--muted-foreground)] transition-colors duration-150 hover:text-[var(--foreground)]"
        >
          + {hidden} مصادر
        </button>
      ) : null}
    </div>
  );
}

/** إجابة المساعد: نص قراءة مباشرة على الصفحة — بلا بطاقات ولا فقاعات. */
export function AssistantMessage({
  content,
  citations,
  onRetry,
  onOpenSources,
}: {
  content: string;
  citations: ChatCitation[];
  onRetry?: () => void;
  onOpenSources: (index: number | null) => void;
}) {
  return (
    <div className="fade-in">
      {citations.length > 0 ? <SourcesRow citations={citations} onOpen={onOpenSources} /> : null}
      <div className="reading mt-2">
        <CitationText text={content} citations={citations} onOpen={onOpenSources} />
      </div>
      <MessageActions content={content} onRetry={onRetry} />
    </div>
  );
}
