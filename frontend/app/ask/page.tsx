"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowUp, ExternalLink, Square } from "lucide-react";
import { Header } from "@/components/chrome";
import { API_URL, api, type Citation, type Madhhab } from "@/lib/api";

type Phase = "idle" | "retrieving" | "streaming" | "done" | "error" | "stopped";

function renderText(text: string) {
  // عناوين بسيطة وتقسيم فقرات دون مكتبات خارجية
  return text.split(/\n{2,}/).map((paragraph, index) => (
    <p key={index} className="whitespace-pre-wrap text-[15px] leading-9">{paragraph}</p>
  ));
}

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [madhhab, setMadhhab] = useState("");
  const [madhhabs, setMadhhabs] = useState<Madhhab[]>([]);
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.madhhabs().then(setMadhhabs).catch(() => {});
  }, []);

  const stop = () => {
    abortRef.current?.abort();
  };

  const ask = async () => {
    const text = question.trim();
    if (!text || phase === "streaming" || phase === "retrieving") return;
    const controller = new AbortController();
    abortRef.current = controller;
    setPhase("retrieving");
    setAnswer("");
    setCitations([]);
    setErrorMessage("");
    try {
      const response = await fetch(`${API_URL}/api/ai/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          question: text,
          ...(madhhab ? { madhhab } : {}),
        }),
      });
      if (!response.ok || !response.body) {
        const detail = await response.text().catch(() => "");
        throw new Error(detail && !detail.startsWith("<") ? detail : `تعذر الاتصال (${response.status})`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";
      let composed = "";
      let paintTimer = 0;
      const paint = () => {
        setAnswer(composed);
        paintTimer = 0;
      };
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let separator = buffer.indexOf("\n\n");
        while (separator >= 0) {
          const rawEvent = buffer.slice(0, separator);
          buffer = buffer.slice(separator + 2);
          for (const line of rawEvent.split("\n")) {
            if (line.startsWith("event:")) currentEvent = line.slice(6).trim();
            else if (line.startsWith("data:")) {
              try {
                const payload = JSON.parse(line.slice(5).trim());
                if (currentEvent === "sources") {
                  setCitations(payload.citations || []);
                  setPhase("streaming");
                } else if (currentEvent === "delta") {
                  composed += payload.text || "";
                  if (!paintTimer) paintTimer = window.setTimeout(paint, 60);
                } else if (currentEvent === "error") {
                  setErrorMessage(payload.message || "تعذر إكمال الرد.");
                  setPhase("error");
                } else if (currentEvent === "done") {
                  setPhase(payload.finish === "cancelled" ? "stopped" : "done");
                }
              } catch {
                // تجاهل أحداث غير مكتملة
              }
            }
          }
          separator = buffer.indexOf("\n\n");
        }
      }
      clearTimeout(paintTimer);
      setAnswer(composed);
      setPhase((current) =>
        current === "retrieving" && !composed && !errorMessage ? "done" : current,
      );
    } catch (error) {
      if (controller.signal.aborted) {
        setPhase("stopped");
        return;
      }
      setErrorMessage(error instanceof Error ? error.message : "تعذر إكمال الرد. حاول من جديد.");
      setPhase("error");
    } finally {
      abortRef.current = null;
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  };

  const busy = phase === "streaming" || phase === "retrieving";

  return (
    <main className="min-h-dvh">
      <Header />
      <div className="mx-auto w-full max-w-3xl px-4 pb-24">
        <h1 className="display-font mt-6 text-2xl font-bold">اسأل المصادر</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          سؤالك يُبحث أولاً في قاعدة النصوص، ثم يُجاب عنه بالاستناد إلى المسائل المسترجعة مع عرض مصادرها.
        </p>
        <div className="mt-6 rounded-[24px] border border-[var(--line)] bg-white p-3 shadow-[0_8px_30px_rgb(25,23,22,0.06)] dark:bg-[#211f1d]">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void ask();
              }
            }}
            rows={3}
            placeholder="مثال: ما حكم صيام يوم عرفة؟"
            className="block w-full resize-none bg-transparent px-3 pt-2 text-sm leading-7 outline-none placeholder:text-[var(--muted)]"
          />
          <div className="mt-2 flex items-center justify-between gap-2">
            <select
              value={madhhab}
              onChange={(event) => setMadhhab(event.target.value)}
              aria-label="حصر الإجابة بمذهب"
              className="rounded-xl border border-[var(--line)] bg-transparent px-3 py-2 text-xs outline-none"
            >
              <option value="">بلا حصر مذهبي</option>
              {madhhabs.map((item) => (
                <option key={item.key} value={item.key}>حصر بـ{item.name_ar}</option>
              ))}
            </select>
            <button
              onClick={() => (busy ? stop() : void ask())}
              disabled={!busy && question.trim().length < 2}
              aria-label={busy ? "إيقاف التوليد" : "إرسال السؤال"}
              className="flex items-center gap-1.5 rounded-full bg-[var(--accent)] px-4 py-2.5 text-xs font-bold text-[var(--ink)] transition hover:brightness-95 disabled:opacity-40"
            >
              {busy ? <Square size={14} strokeWidth={2} /> : <ArrowUp size={16} strokeWidth={2} />}
              {busy ? "إيقاف" : "اسأل"}
            </button>
          </div>
        </div>

        {phase === "retrieving" ? (
          <p className="soft-pulse mt-8 text-sm font-bold">جارٍ البحث في قاعدة المصادر…</p>
        ) : null}

        {answer ? (
          <section className="markdown-response mt-8 rounded-2xl border border-[var(--line)] bg-white p-6 dark:bg-[#1b1a18]">
            {renderText(answer)}
          </section>
        ) : null}

        {errorMessage ? (
          <div role="alert" className="app-error mt-6 rounded-xl border px-4 py-3 text-sm">{errorMessage}</div>
        ) : null}

        {citations.length > 0 ? (
          <section className="mt-8">
            <h2 className="text-sm font-bold">المصادر المستخدمة</h2>
            <div className="mt-3 space-y-3">
              {citations.map((citation) => (
                <article key={citation.index} className="rounded-2xl border border-[var(--line)] bg-white p-4 dark:bg-[#1b1a18]">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--muted)]">
                    <span className="source-chip"><span className="source-dot" />[{citation.index}]</span>
                    {citation.scholar ? <span className="source-chip"><span className="source-dot" />{citation.scholar}</span> : null}
                    <span className="source-chip"><span className="source-dot" />{citation.book_title}</span>
                    {citation.issue_number !== null ? (
                      <span className="source-chip"><span className="source-dot" />المسألة {citation.issue_number}</span>
                    ) : null}
                    {citation.madhhab ? <span className="source-chip"><span className="source-dot" />{citation.madhhab}</span> : null}
                  </div>
                  {citation.section_path ? (
                    <p className="mt-2 text-xs text-[var(--muted)]">{citation.section_path}</p>
                  ) : null}
                  <p className="mt-2 line-clamp-3 text-xs leading-6 text-[var(--muted)]">{citation.text_original.slice(0, 220)}…</p>
                  <div className="mt-3 flex gap-2">
                    <Link href={`/issue/${citation.issue_id}`} className="rounded-full bg-[var(--ink)] px-3 py-1.5 text-[11px] font-bold text-[var(--paper)]">
                      النص الكامل
                    </Link>
                    <a href={citation.source_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 rounded-full border border-[var(--line)] px-3 py-1.5 text-[11px] font-bold">
                      المصدر الأصلي <ExternalLink size={12} />
                    </a>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ) : null}
        <div ref={endRef} />
      </div>
    </main>
  );
}
