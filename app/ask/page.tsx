"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Square } from "lucide-react";
import { Composer } from "@/components/composer";
import { SiteHeader } from "@/components/site-header";
import { CitationText, SourceDrawer } from "@/components/source-drawer";
import { API_URL, type Citation } from "@/lib/api";

type Phase = "idle" | "retrieving" | "streaming" | "done" | "error" | "stopped";

function AskInner() {
  const params = useSearchParams();
  const question = params.get("q") || "";
  const madhhab = params.get("madhhab") || undefined;

  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [phase, setPhase] = useState<Phase>(question ? "retrieving" : "idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const answerRef = useRef<HTMLDivElement>(null);

  const stop = () => abortRef.current?.abort();

  const run = useCallback(
    (text: string, filter?: string) => {
      if (!text.trim()) return;
      const controller = new AbortController();
      abortRef.current = controller;
      setPhase("retrieving");
      setAnswer("");
      setCitations([]);
      setErrorMessage("");
      setActiveCitation(null);
      setDrawerOpen(false);
      (async () => {
        try {
          const response = await fetch(`${API_URL}/api/ai/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            signal: controller.signal,
            body: JSON.stringify({
              question: text,
              ...(filter ? { madhhab: filter } : {}),
            }),
          });
          if (!response.ok || !response.body) {
            const detail = await response.text().catch(() => "");
            throw new Error(
              detail && !detail.startsWith("<") ? detail : `تعذر الاتصال (${response.status})`,
            );
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
                      if (!paintTimer) paintTimer = window.setTimeout(paint, 80);
                    } else if (currentEvent === "error") {
                      setErrorMessage(payload.message || "تعذر إكمال الرد.");
                      setPhase("error");
                    } else if (currentEvent === "done") {
                      setPhase(payload.finish === "cancelled" ? "stopped" : "done");
                    }
                  } catch {
                    // أحداث غير مكتملة تُتجاهل
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
        }
      })();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  useEffect(() => {
    if (question) run(question, madhhab ?? undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const busy = phase === "streaming" || phase === "retrieving";
  const openCitation = (index: number) => {
    setActiveCitation(index);
    setDrawerOpen(true);
  };

  return (
    <div className="flex min-h-dvh flex-col">
      <main className="mx-auto w-full max-w-3xl flex-1 px-5 sm:px-6">
        {phase === "idle" && !question ? (
          <div className="flex h-[60dvh] items-center justify-center">
            <div className="w-full max-w-[728px]">
              <Composer variant="hero" />
            </div>
          </div>
        ) : (
          <>
            {/* السؤال */}
            <div className="pt-10">
              <p className="text-[16px] font-medium leading-7 text-[var(--ink)]">{question}</p>
            </div>

            {/* حالة الاسترجاع */}
            {phase === "retrieving" ? (
              <p className="quiet-dot mt-8 text-[13px] text-[var(--muted)]">يبحث في المصادر…</p>
            ) : null}

            {/* خط الاسترجاع الصامت */}
            {citations.length > 0 ? (
              <button
                onClick={() => setDrawerOpen(true)}
                className="fade-in mt-6 text-[12.5px] text-[var(--muted)] transition-colors duration-150 hover:text-[var(--ink)]"
              >
                استُشهد {citations.length} مصدراً
              </button>
            ) : null}

            {/* الإجابة كنص قراءة */}
            {answer ? (
              <div ref={answerRef} className="reading fade-in mt-3">
                <CitationText text={answer} citations={citations} onOpen={openCitation} />
              </div>
            ) : null}
            {phase === "streaming" && answer ? (
              <span className="quiet-dot mt-1 inline-block size-1.5 rounded-full bg-[var(--muted)]" />
            ) : null}

            {errorMessage ? (
              <div role="alert" className="fade-in mt-6 text-[14px] leading-7 text-[var(--muted-strong)]">
                {errorMessage}
              </div>
            ) : null}
            {phase === "stopped" ? (
              <p className="fade-in mt-4 text-[12.5px] text-[var(--muted)]">أُوقف الرد.</p>
            ) : null}
          </>
        )}
      </main>

      {/* الـcomposer يرسو أسفل الصفحة أثناء المحادثة */}
      {question ? (
        <div className="sticky bottom-0 mt-10 bg-gradient-to-t from-[var(--paper)] from-70% pb-4 pt-3">
          <div className="mx-auto w-full max-w-3xl px-5 sm:px-6">
            <Composer variant="docked" />
            <div className="mt-2 flex items-center justify-end">
              {busy ? (
                <button
                  onClick={stop}
                  className="flex items-center gap-1.5 text-[12px] text-[var(--muted)] transition-colors duration-150 hover:text-[var(--ink)]"
                >
                  <Square size={10} strokeWidth={2} /> إيقاف
                </button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {drawerOpen ? (
        <SourceDrawer
          citations={citations}
          activeIndex={activeCitation}
          onClose={() => {
            setDrawerOpen(false);
            setActiveCitation(null);
          }}
        />
      ) : null}
    </div>
  );
}

export default function AskPage() {
  return (
    <div className="min-h-dvh">
      <SiteHeader />
      <Suspense fallback={<main className="mx-auto max-w-3xl px-5 pt-10 text-[13px] text-[var(--muted)]">…</main>}>
        <AskInner />
      </Suspense>
    </div>
  );
}
