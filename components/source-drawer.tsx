"use client";

import { useEffect } from "react";
import { ArrowUpLeft, X } from "lucide-react";
import type { ChatCitation } from "@/lib/api";

/**
 * لوحة المصادر: تظهر كطبقة ثانوية بنفس لون الخلفية،
 * بفاصل جانبي رقيق وقائمة نصية نظيفة — لا بطاقات.
 */
export function SourceDrawer({
  citations,
  activeIndex,
  onClose,
}: {
  citations: ChatCitation[];
  activeIndex: number | null;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const ordered = activeIndex
    ? [...citations].sort((a, b) =>
        a.index === activeIndex ? -1 : b.index === activeIndex ? 1 : a.index - b.index,
      )
    : citations;

  return (
    <div className="fixed inset-0 z-40" onClick={onClose}>
      <div className="absolute inset-0 bg-[var(--overlay)] transition-opacity duration-200" />
      <div
        onClick={(event) => event.stopPropagation()}
        className="drawer-in absolute inset-y-0 end-0 flex w-full max-w-[440px] flex-col border-s border-[var(--border)] bg-[var(--background)] sm:w-[420px]"
      >
        <div className="flex items-center justify-between px-5 pb-3 pt-5">
          <h2 className="text-[14px] font-medium text-[var(--foreground)]">
            المصادر المستخدمة
            <span className="ms-1.5 text-[var(--muted-foreground)]">{citations.length}</span>
          </h2>
          <button
            onClick={onClose}
            aria-label="إغلاق"
            className="grid size-8 place-items-center rounded-full text-[var(--muted-foreground)] transition-colors duration-150 hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
          >
            <X size={15} strokeWidth={1.6} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 pb-8">
          {ordered.map((citation) => (
            <article key={citation.index} className="hairline-b py-4 last:border-0">
              <div className="flex items-baseline gap-2">
                <span className="text-[12px] tabular-nums text-[var(--muted-foreground)]">[{citation.index}]</span>
                <h3 className="min-w-0 text-[14px] font-medium leading-6 text-[var(--foreground)]">
                  {citation.title}
                </h3>
              </div>
              <p className="mt-0.5 ps-6 text-[11.5px] text-[var(--muted-foreground)]">{citation.provider_label}</p>
              {citation.detail ? (
                <p className="mt-0.5 ps-6 text-[12.5px] leading-5 text-[var(--muted-foreground)]">{citation.detail}</p>
              ) : null}
              <p className="mt-2.5 ps-6 text-[13.5px] leading-7 text-[var(--muted-foreground)]">
                {citation.text.length > 420 ? `${citation.text.slice(0, 420)}…` : citation.text}
              </p>
              <div className="mt-2.5 flex items-center gap-4 ps-6">
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[12.5px] text-[var(--muted-foreground)] underline-offset-4 transition-colors duration-150 hover:text-[var(--foreground)] hover:underline"
                >
                  فتح المصدر <ArrowUpLeft size={11} strokeWidth={1.8} />
                </a>
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * الاستشهادات المضمنة داخل نص الإجابة: تحليل [1] [2]…
 * وعرضها كأزرار مرجعية صغيرة منخفضة الضوضاء.
 */
export function CitationText({
  text,
  citations,
  onOpen,
}: {
  text: string;
  citations: ChatCitation[];
  onOpen: (index: number) => void;
}) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((part, index) => {
        const match = /^\[(\d+)\]$/.exec(part);
        if (match) {
          const index_ = Number(match[1]);
          const exists = citations.some((citation) => citation.index === index_);
          if (!exists) return <span key={index}>{part}</span>;
          return (
            <button
              key={index}
              onClick={() => onOpen(index_)}
              aria-label={`المصدر ${index_}`}
              className="mx-0.5 inline-grid h-[17px] min-w-[17px] translate-y-[-2px] place-items-center rounded-[5px] border border-[var(--border)] bg-[var(--surface)] px-1 align-middle text-[10.5px] tabular-nums text-[var(--muted-foreground)] transition-colors duration-150 hover:border-[var(--border-strong)] hover:text-[var(--foreground)]"
            >
              {index_}
            </button>
          );
        }
        return part.endsWith("\n") ? (
          <span key={index} className="whitespace-pre-wrap">
            {part}
          </span>
        ) : (
          <span key={index} className="whitespace-pre-wrap">
            {part}
          </span>
        );
      })}
    </>
  );
}
