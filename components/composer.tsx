"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUp, BookOpen, Search, SlidersHorizontal, Sparkles, Square, X } from "lucide-react";
import { api, type Madhhab, type Scholar, type SourceInfo } from "@/lib/api";

export type Mode = "search" | "ask";
export type ResearchMode = "auto" | "islamic" | "web" | "expanded";

export interface ComposerOptions {
  researchMode: ResearchMode;
  madhhab?: string;
  scholar?: string;
  book?: string;
}

const RESEARCH_MODES: { key: ResearchMode; label: string }[] = [
  { key: "auto", label: "تلقائي" },
  { key: "islamic", label: "المصادر الإسلامية" },
  { key: "web", label: "الويب" },
  { key: "expanded", label: "بحث موسع" },
];

interface Meta {
  madhhabs: Madhhab[];
  scholars: Scholar[];
  books: { id: number; title: string }[];
  sources: SourceInfo[];
}

function useMeta() {
  const [meta, setMeta] = useState<Meta | null>(null);
  useEffect(() => {
    let cancelled = false;
    Promise.all([api.madhhabs(), api.scholars(), api.books(), api.sources()])
      .then(([madhhabs, scholars, books, sources]) => {
        if (!cancelled) {
          setMeta({
            madhhabs,
            scholars,
            books: books.map((book) => ({ id: book.id, title: book.title })),
            sources,
          });
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  return meta;
}

function ResearchPopover({
  meta,
  options,
  onChange,
  onClose,
}: {
  meta: Meta | null;
  options: ComposerOptions;
  onChange: (options: ComposerOptions) => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const labelClass = "mb-1 block text-[11.5px] text-[var(--muted-foreground)]";
  const selectClass =
    "w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-2.5 py-1.5 text-[12.5px] text-[var(--foreground)] outline-none transition-colors duration-150 focus:border-[var(--border-strong)]";

  return (
    <div
      ref={ref}
      className="fade-in absolute bottom-[calc(100%+10px)] end-0 z-20 w-[290px] rounded-2xl border border-[var(--border)] bg-[var(--background)] p-4"
    >
      <p className="mb-2 text-[12px] font-medium text-[var(--foreground)]">وضع البحث</p>
      <div className="space-y-0.5">
        {RESEARCH_MODES.map((mode) => (
          <button
            key={mode.key}
            onClick={() => onChange({ ...options, researchMode: mode.key })}
            aria-pressed={options.researchMode === mode.key}
            className={`flex h-8 w-full items-center rounded-lg px-2.5 text-[12.5px] transition-colors duration-150 ${
              options.researchMode === mode.key
                ? "bg-[var(--surface-hover)] text-[var(--foreground)]"
                : "text-[var(--muted-foreground)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
            }`}
          >
            {mode.label}
          </button>
        ))}
      </div>

      <p className="mb-2 mt-4 text-[12px] font-medium text-[var(--foreground)]">المصادر</p>
      <div className="space-y-2.5">
        <div>
          <label className={labelClass}>المذهب</label>
          <select
            value={options.madhhab ?? ""}
            onChange={(event) => onChange({ ...options, madhhab: event.target.value || undefined })}
            className={selectClass}
          >
            <option value="">تلقائي</option>
            {(meta?.madhhabs ?? []).map((item) => (
              <option key={item.key} value={item.key}>
                {item.name_ar}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>المرجع</label>
          <select
            value={options.scholar ?? ""}
            onChange={(event) => onChange({ ...options, scholar: event.target.value || undefined })}
            className={selectClass}
          >
            <option value="">تلقائي</option>
            {(meta?.scholars ?? []).map((item) => (
              <option key={item.key} value={item.key}>
                {item.name_ar}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>الكتاب</label>
          <select
            value={options.book ?? ""}
            onChange={(event) => onChange({ ...options, book: event.target.value || undefined })}
            className={selectClass}
          >
            <option value="">الكل</option>
            {(meta?.books ?? []).map((item) => (
              <option key={item.id} value={String(item.id)}>
                {item.title}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function OptionToken({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex h-7 items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] py-0 pe-1.5 ps-2.5 text-[12px] text-[var(--muted)]">
      {label}
      <button
        onClick={onRemove}
        aria-label={`إزالة ${label}`}
        className="grid size-4 place-items-center rounded text-[var(--muted-foreground)] transition-colors duration-150 hover:text-[var(--foreground)]"
      >
        <X size={10} strokeWidth={2} />
      </button>
    </span>
  );
}

export function Composer({
  initialQuery = "",
  initialMode = "ask",
  variant = "hero",
  suggestions,
  busy = false,
  onStop,
  onChatSubmit,
  onSearchSubmit,
}: {
  initialQuery?: string;
  initialMode?: Mode;
  variant?: "hero" | "docked";
  suggestions?: string[];
  busy?: boolean;
  onStop?: () => void;
  onChatSubmit?: (message: string, options: ComposerOptions) => void;
  onSearchSubmit?: (message: string, options: ComposerOptions) => void;
}) {
  const router = useRouter();
  const meta = useMeta();
  const [query, setQuery] = useState(initialQuery);
  const [mode, setMode] = useState<Mode>(initialMode);
  const [options, setOptions] = useState<ComposerOptions>({ researchMode: "auto" });
  const [toolsOpen, setToolsOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const tokenText = (key: "madhhab" | "scholar" | "book", value: string): string => {
    if (!meta) return value;
    if (key === "madhhab") return meta.madhhabs.find((item) => item.key === value)?.name_ar ?? value;
    if (key === "scholar") return meta.scholars.find((item) => item.key === value)?.name_ar ?? value;
    return meta.books.find((item) => String(item.id) === value)?.title ?? value;
  };

  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  useEffect(resize, [query, resize]);

  const activeTokens = (["madhhab", "scholar", "book"] as const)
    .filter((key) => options[key])
    .map((key) => ({
      key,
      label: `${key === "book" ? "الكتاب" : key === "scholar" ? "المرجع" : "المذهب"}: ${tokenText(key, options[key] as string)}`,
    }));

  const submit = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed || busy) return;
    const payloadOptions = { ...options };
    if (onChatSubmit) {
      onChatSubmit(trimmed, payloadOptions);
    } else if (onSearchSubmit) {
      onSearchSubmit(trimmed, payloadOptions);
    } else {
      const params = new URLSearchParams();
      params.set("q", trimmed);
      if (payloadOptions.madhhab) params.set("madhhab", payloadOptions.madhhab);
      if (payloadOptions.scholar) params.set("scholar", payloadOptions.scholar);
      if (payloadOptions.book) params.set("book", payloadOptions.book);
      router.push(`/search?${params.toString()}`);
    }
    setQuery("");
  }, [query, options, busy, onChatSubmit, onSearchSubmit, router]);

  const hasInput = query.trim().length > 0;
  const searchModeActive = mode === "search";

  return (
    <div className="w-full">
      {activeTokens.length > 0 ? (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {activeTokens.map((token) => (
            <OptionToken
              key={token.key}
              label={token.label}
              onRemove={() => {
                const next = { ...options };
                delete next[token.key];
                setOptions(next);
              }}
            />
          ))}
        </div>
      ) : null}

      <div className="relative rounded-[22px] border border-[var(--border)] bg-[var(--composer)] transition-colors duration-200 focus-within:border-[var(--border-strong)]">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          rows={1}
          autoFocus={variant === "hero"}
          disabled={busy}
          placeholder="اسأل عن مسألة شرعية، حديث، حكم أو موضوع إسلامي…"
          aria-label="حقل السؤال"
          className="block max-h-[200px] w-full resize-none bg-transparent px-4 pt-3.5 text-[16px] font-normal leading-7 text-[var(--foreground)] outline-none placeholder:text-[var(--muted-foreground)] disabled:opacity-60"
        />
        <div className="flex items-center justify-between gap-2 px-2.5 pb-2.5 pt-1.5">
          <div className="flex min-w-0 items-center gap-0.5">
            <div className="relative">
              <button
                onClick={() => setToolsOpen((open) => !open)}
                aria-expanded={toolsOpen}
                aria-label="إعدادات البحث والمصادر"
                className={`flex h-8 items-center gap-1.5 rounded-lg px-2 text-[12.5px] transition-colors duration-150 ${
                  toolsOpen || activeTokens.length > 0 || options.researchMode !== "auto"
                    ? "text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
                }`}
              >
                <SlidersHorizontal size={14} strokeWidth={1.7} />
                <span className="hidden sm:inline">
                  {options.researchMode === "auto"
                    ? "بحث"
                    : RESEARCH_MODES.find((item) => item.key === options.researchMode)?.label}
                </span>
              </button>
              {toolsOpen ? (
                <ResearchPopover
                  meta={meta}
                  options={options}
                  onChange={setOptions}
                  onClose={() => setToolsOpen(false)}
                />
              ) : null}
            </div>
            <div className="flex items-center rounded-lg bg-[var(--surface)] p-0.5" role="tablist" aria-label="الوضع">
              <button
                onClick={() => setMode("ask")}
                aria-pressed={mode === "ask"}
                className={`flex h-7 items-center gap-1.5 rounded-md px-2 text-[12px] transition-colors duration-150 ${
                  mode === "ask"
                    ? "bg-[var(--composer)] text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                }`}
              >
                <Sparkles size={12} strokeWidth={1.7} />
                اسأل
              </button>
              <button
                onClick={() => setMode("search")}
                aria-pressed={mode === "search"}
                className={`flex h-7 items-center gap-1.5 rounded-md px-2 text-[12px] transition-colors duration-150 ${
                  mode === "search"
                    ? "bg-[var(--composer)] text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                }`}
              >
                <Search size={12} strokeWidth={1.7} />
                بحث
              </button>
            </div>
            {searchModeActive ? (
              <button
                onClick={() => setToolsOpen(true)}
                aria-label="فلاتر البحث"
                title="فلاتر البحث"
                className="grid size-8 place-items-center rounded-lg text-[var(--muted-foreground)] transition-colors duration-150 hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
              >
                <BookOpen size={14} strokeWidth={1.7} />
              </button>
            ) : null}
          </div>
          <button
            onClick={() => (busy && onStop ? onStop() : submit())}
            disabled={!busy && !hasInput}
            aria-label={busy ? "إيقاف الرد" : "إرسال"}
            className="grid size-8 shrink-0 place-items-center rounded-full bg-[var(--foreground)] text-[var(--background)] transition-opacity duration-150 hover:opacity-85 disabled:opacity-25"
          >
            {busy ? <Square size={12} strokeWidth={2} /> : <ArrowUp size={15} strokeWidth={2} />}
          </button>
        </div>
      </div>

      {suggestions && suggestions.length > 0 ? (
        <div className="mt-4 flex flex-wrap justify-center gap-x-6 gap-y-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => {
                setQuery(suggestion);
                textareaRef.current?.focus();
              }}
              className="text-[13px] text-[var(--muted-foreground)] transition-colors duration-150 hover:text-[var(--foreground)]"
            >
              {suggestion}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
