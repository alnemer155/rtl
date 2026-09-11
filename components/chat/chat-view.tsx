"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown } from "lucide-react";
import { Composer, type ComposerOptions } from "@/components/composer";
import { AssistantMessage, UserMessage } from "@/components/chat/messages";
import { ResearchProgress } from "@/components/chat/research-progress";
import { CitationText, SourceDrawer } from "@/components/source-drawer";
import { streamChat, type ChatCitation } from "@/lib/api";

interface ChatMessageView {
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[];
}

type Phase = "idle" | "searching" | "streaming" | "error";

/**
 * تجربة المحادثة: الصفحة الرئيسية تتحول في مكانها إلى محادثة،
 * الإجابة نص قراءة هادئ (وزن 400) مع استشهادات مضمنة ودرج مصادر.
 */
export function ChatView({
  initialMessages = [],
  initialConversationId,
  initialTitle,
}: {
  initialMessages?: ChatMessageView[];
  initialConversationId?: string;
  initialTitle?: string;
}) {
  const [messages, setMessages] = useState<ChatMessageView[]>(initialMessages);
  const [conversationId, setConversationId] = useState<string | undefined>(initialConversationId);
  const [title] = useState(initialTitle ?? "");
  const [phase, setPhase] = useState<Phase>("idle");
  const [progressLines, setProgressLines] = useState<string[]>([]);
  const [streamText, setStreamText] = useState("");
  const [streamCitations, setStreamCitations] = useState<ChatCitation[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [showScrollDown, setShowScrollDown] = useState(false);
  const abortRef = useRef<{ abort: () => void } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const streamTextRef = useRef("");
  const streamCitationsRef = useRef<ChatCitation[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);

  useEffect(() => {
    streamTextRef.current = streamText;
    streamCitationsRef.current = streamCitations;
  }, [streamText, streamCitations]);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottomRef.current = distance < 120;
    setShowScrollDown(distance > 300);
  };

  const scrollToBottom = () => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  };

  useEffect(() => {
    if (stickToBottomRef.current) {
      bottomRef.current?.scrollIntoView({ block: "end" });
    }
  }, [messages, streamText, progressLines]);

  const stop = () => abortRef.current?.abort();

  const submit = useCallback(
    (message: string, options: ComposerOptions) => {
      const trimmed = message.trim();
      if (!trimmed || phase === "searching" || phase === "streaming") return;
      abortRef.current = null;
      stickToBottomRef.current = true;
      setMessages((current) => [...current, { role: "user", content: trimmed, citations: [] }]);
      setPhase("searching");
      setProgressLines(["نفهم السؤال…"]);
      setStreamText("");
      setStreamCitations([]);
      setErrorMessage("");

      const stream = streamChat(
        {
          message: trimmed,
          ...(conversationId ? { conversation_id: conversationId } : {}),
          ...(options.researchMode !== "auto" ? { research_mode: options.researchMode } : {}),
          ...(options.madhhab ? { madhhab: options.madhhab } : {}),
          ...(options.scholar ? { scholar: options.scholar } : {}),
          ...(options.book ? { book: Number(options.book) } : {}),
        },
        {
          onMeta: (payload) => {
            if (payload.conversation_id !== conversationId) {
              setConversationId(payload.conversation_id);
              // pushState فقط: لا إعادة تحميل — المكوّن يحتفظ بحالة البث
              window.history.replaceState(null, "", `/chat/${payload.conversation_id}`);
            }
          },
          onStatus: (payload) => {
            if (payload.line) {
              setProgressLines((currentLines) => [...currentLines, payload.line]);
              if (payload.line.startsWith("يبحث")) setPhase("searching");
            }
          },
          onSources: (payload) => {
            setStreamCitations(payload.citations || []);
          },
          onDelta: (payload) => {
            if (payload.text) {
              setPhase("streaming");
              setStreamText((current) => current + payload.text);
            }
          },
          onError: (payload) => {
            setErrorMessage(payload.message || "تعذر إكمال الرد.");
            setPhase("error");
          },
          onDone: () => {
            const content = streamTextRef.current;
            if (content.trim()) {
              setMessages((current) => [
                ...current,
                { role: "assistant", content, citations: streamCitationsRef.current },
              ]);
            }
            setStreamText("");
            setStreamCitations([]);
            setProgressLines([]);
            setPhase((current) => (current === "error" ? "error" : "idle"));
            window.dispatchEvent(new Event("masadir:conversations-changed"));
          },
          onAbort: () => {
            if (streamTextRef.current) {
              setMessages((current) => [
                ...current,
                {
                  role: "assistant",
                  content: streamTextRef.current,
                  citations: streamCitationsRef.current,
                },
              ]);
            }
            setStreamText("");
            setProgressLines([]);
            setPhase("idle");
            window.dispatchEvent(new Event("masadir:conversations-changed"));
          },
        },
      );
      abortRef.current = stream;
    },
    [conversationId, phase],
  );

  const retryLast = () => {
    const lastUser = [...messages].reverse().find((message) => message.role === "user");
    if (lastUser) {
      setMessages((current) => {
        const copy = [...current];
        if (copy.at(-1)?.role === "assistant") copy.pop();
        return copy;
      });
      submit(lastUser.content, { researchMode: "auto" });
    }
  };

  const openCitation = (index: number | null) => {
    setActiveCitation(index);
    setDrawerOpen(true);
  };

  const empty = messages.length === 0 && phase === "idle" && !streamText;
  const busy = phase === "searching" || phase === "streaming";
  const activeCitations = streamCitations.length > 0 ? streamCitations : messages.at(-1)?.citations ?? [];

  return (
    <div className="flex min-h-dvh flex-col">
      {/* ترويسة المحادثة: سياق بسيط فقط */}
      <div className="sticky top-0 z-10 hidden h-12 items-center justify-between bg-[var(--background)] px-5 lg:flex">
        <span className="max-w-[50%] truncate text-[13px] text-[var(--muted-foreground)]">
          {title || (empty ? "محادثة جديدة" : "محادثة")}
        </span>
      </div>

      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-y-auto px-5 sm:px-6"
        style={{ maxHeight: "calc(100dvh - 48px)" }}
      >
        {empty ? (
          <div className="flex flex-1 flex-col items-center justify-center pb-20 pt-[18dvh]">
            <p className="mb-1 text-[26px] font-medium leading-9 text-[var(--foreground)]">
              كيف أقدر أساعدك اليوم؟
            </p>
            <div className="mt-7 w-full max-w-[760px]">
              <Composer
                variant="hero"
                initialMode="ask"
                busy={busy}
                onStop={stop}
                onChatSubmit={submit}
                suggestions={[
                  "ما حكم صلاة المسافر عند السيد السيستاني؟",
                  "ابحث عن حديث في بر الوالدين",
                  "قارن حكم زكاة الفطر بين المذاهب",
                  "اشرح لي معنى حديث معين",
                ]}
              />
            </div>
          </div>
        ) : (
          <div className="flex-1 pb-8 pt-6">
            {messages.map((message, index) => (
              <div key={index} className="mb-6">
                {message.role === "user" ? (
                  <UserMessage content={message.content} />
                ) : (
                  <AssistantMessage
                    content={message.content}
                    citations={message.citations}
                    onRetry={index === messages.length - 1 ? retryLast : undefined}
                    onOpenSources={openCitation}
                  />
                )}
              </div>
            ))}

            {phase === "searching" || (phase === "streaming" && !streamText) ? (
              <ResearchProgress lines={progressLines} done={false} />
            ) : null}
            {streamText ? (
              <div className="fade-in">
                <div className="reading">
                  <CitationText
                    text={streamText}
                    citations={streamCitations}
                    onOpen={openCitation}
                  />
                </div>
              </div>
            ) : null}
            {phase === "error" ? (
              <div role="alert" className="fade-in mt-2 text-[14px] leading-7 text-[var(--muted)]">
                {errorMessage}
                {messages.length > 0 ? (
                  <button
                    onClick={retryLast}
                    className="ms-3 text-[13px] text-[var(--foreground)] underline-offset-4 hover:underline"
                  >
                    إعادة المحاولة
                  </button>
                ) : null}
              </div>
            ) : null}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* زر العودة للأسفل عندما يصعد المستخدم */}
      {showScrollDown && !empty ? (
        <button
          onClick={scrollToBottom}
          aria-label="العودة للأسفل"
          className="fade-in fixed bottom-28 start-1/2 z-10 grid size-9 -translate-x-1/2 place-items-center rounded-full border border-[var(--border)] bg-[var(--composer)] text-[var(--muted-foreground)] transition-colors duration-150 hover:text-[var(--foreground)] rtl:translate-x-1/2"
        >
          <ArrowDown size={15} />
        </button>
      ) : null}

      {/* الـcomposer يرسو أسفل الشاشة في المحادثة */}
      {!empty ? (
        <div className="sticky bottom-0 bg-gradient-to-t from-[var(--background)] from-75% pb-4 pt-3 safe-bottom">
          <div className="mx-auto w-full max-w-3xl px-5 sm:px-6">
            <Composer
              variant="docked"
              initialMode="ask"
              busy={busy}
              onStop={stop}
              onChatSubmit={submit}
            />
          </div>
        </div>
      ) : null}

      {drawerOpen ? (
        <SourceDrawer
          citations={activeCitations}
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

