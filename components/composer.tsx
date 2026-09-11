"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUp, Search, Sparkles, SlidersHorizontal, X } from "lucide-react";
import { api, type Madhhab, type Scholar, type SourceInfo } from "@/lib/api";

export type Mode = "search" | "ask";

export interface FilterState {
  madhhab?: string;
  scholar?: string;
  book?: string;
  source?: string;
}

const EMPTY_FILTERS: FilterState = {};

interface Meta {
  madhhabs: Madhhab[];
  scholars: Scholar[];
  books: { id: number; title: string }[];
  sources: SourceInfo[];
}

function useMeta(enabled: boolean) {
  const [meta, setMeta] = useState<Meta | null>(null);
  useEffect(() => {
    if (!enabled) return;
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
  }, [enabled]);
  return meta;
}

function FilterPopover({
  meta,
  filters,
  onChange,
  onClose,
}: {
  meta: Meta | null;
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const onClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) onClose();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [onClose]);

  const selectClass =
    "w-full rounded-xl border border-[var(--line)] bg-[var(--paper)] px-3 py-2 text-[13px] text-[var(--ink)] outline-none transition-colors duration-150 focus:border-[var(--line-strong)]";
  const labelClass = "mb-1.5 block text-[12px] text-[var(--muted)]";

  const hasAny = Object.values(filters).some(Boolean);

  return (
    <div
      ref={ref}
      className="fade-in absolute inset-x-3 bottom-[calc(100%+8px)] z-20 rounded-2xl border border-[var(--line)] bg-[var(--raise)] p-4 sm:inset-x-auto sm:bottom-[calc(100%+10px)] sm:end-0 sm:w-[300px] sm:p-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[13px] font-medium text-[var(--ink)]">حصر البحث</span>
        {hasAny ? (
          <button
            onClick={() => onChange(EMPTY_FILTERS)}
            className="text-[12px] text-[var(--muted)] transition-colors duration-150 hover:text-[var(--ink)]"
          >
            مسح الكل
          </button>
        ) : null}
      </div>
      <div className="space-y-3">
        <div>
          <label className={labelClass}>المذهب</label>
          <select
            value={filters.madhhab ?? ""}
            onChange={(event) => onChange({ ...filters, madhhab: event.target.value || undefined })}
            className={selectClass}
          >
            <option value="">كل المذاهب</option>
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
            value={filters.scholar ?? ""}
            onChange={(event) => onChange({ ...filters, scholar: event.target.value || undefined })}
            className={selectClass}
          >
            <option value="">كل المراجع</option>
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
            value={filters.book ?? ""}
            onChange={(event) => onChange({ ...filters, book: event.target.value || undefined })}
            className={selectClass}
          >
            <option value="">كل الكتب</option>
            {(meta?.books ?? []).map((item) => (
              <option key={item.id} value={String(item.id)}>
                {item.title}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>المصدر</label>
          <select
            value={filters.source ?? ""}
            onChange={(event) => onChange({ ...filters, source: event.target.value || undefined })}
            className={selectClass}
          >
            <option value="">كل المصادر</option>
            {(meta?.sources ?? []).map((item) => (
              <option key={item.key} value={item.key}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function FilterToken({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex h-7 items-center gap-1.5 rounded-full border border-[var(--line)] bg-[var(--paper)] py-0 pe-2 ps-3 text-[12px] text-[var(--muted-strong)]">
      {label}
      <button
        onClick={onRemove}
        aria-label={`إزالة ${label}`}
        className="grid size-4 place-items-center rounded-full text-[var(--muted)] transition-colors duration-150 hover:bg-[var(--wash)] hover:text-[var(--ink)]"
      >
        <X size={10} strokeWidth={2} />
      </button>
    </span>
  );
}

export function Composer({
  initialQuery = "",
  initialMode = "search",
  initialFilters = EMPTY_FILTERS,
  variant = "hero",
  suggestions,
  autoSubmit = false,
}: {
  initialQuery?: string;
  initialMode?: Mode;
  initialFilters?: FilterState;
  variant?: "hero" | "docked";
  suggestions?: string[];
  autoSubmit?: boolean;
}) {
  const router = useRouter();
  const meta = useMeta(true);
  const [query, setQuery] = useState(initialQuery);
  const [mode, setMode] = useState<Mode>(initialMode);
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const submittedRef = useRef(false);

  const metaLoaded = meta !== null;
  const filterLabels: { key: keyof FilterState; label: string }[] = [
    { key: "madhhab", label: "المذهب" },
    { key: "scholar", label: "المرجع" },
    { key: "book", label: "الكتاب" },
    { key: "source", label: "المصدر" },
  ];
  const tokenText = (key: keyof FilterState, value: string): string => {
    if (!meta) return value;
    if (key === "madhhab") return meta.madhhabs.find((item) => item.key === value)?.name_ar ?? value;
    if (key === "scholar") return meta.scholars.find((item) => item.key === value)?.name_ar ?? value;
    if (key === "book") return meta.books.find((item) => String(item.id) === value)?.title ?? value;
    return meta.sources.find((item) => item.key === value)?.name ?? value;
  };

  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  useEffect(resize, [query, resize]);

  const submit = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed) return;
    const params = new URLSearchParams();
    params.set("q", trimmed);
    if (filters.madhhab) params.set("madhhab", filters.madhhab);
    if (filters.scholar) params.set("scholar", filters.scholar);
    if (filters.book) params.set("book", filters.book);
    if (filters.source) params.set("source", filters.source);
    const target = mode === "ask" ? "/ask" : "/search";
    router.push(`${target}?${params.toString()}`);
  }, [query, filters, mode, router]);

  // فتح صفحة السؤال تلقائياً عند وصول ?q= إلى صفحة بها composer ذي autoSubmit
  useEffect(() => {
    if (autoSubmit && initialQuery && !submittedRef.current) {
      submittedRef.current = true;
      submit();
    }
  }, [autoSubmit, initialQuery, submit]);

  const activeTokens = filterLabels.filter(({ key }) => filters[key]);

  return (
    <div className="w-full">
      {activeTokens.length > 0 ? (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {activeTokens.map(({ key, label }) => (
            <FilterToken
              key={key}
              label={`${label}: ${tokenText(key, filters[key] as string)}`}
              onRemove={() => {
                const next = { ...filters };
                delete next[key];
                setFilters(next);
              }}
            />
          ))}
        </div>
      ) : null}

      <div
        className={`relative rounded-[24px] border border-[var(--line)] bg-[var(--raise)] transition-colors duration-200 focus-within:border-[var(--line-strong)] ${
          variant === "hero" ? "" : ""
        }`}
      >
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
          placeholder="اسأل عن مسألة، حكم، حديث أو كتاب…"
          aria-label="حقل السؤال والبحث"
          className="block max-h-[200px] w-full resize-none bg-transparent px-4 pt-3.5 text-[16px] leading-7 text-[var(--ink)] outline-none placeholder:text-[var(--muted)]"
        />
        <div className="flex items-center justify-between gap-2 px-2.5 pb-2.5 pt-1">
          <div className="flex min-w-0 items-center gap-1">
            <div className="flex items-center rounded-full bg-[var(--stone)] p-0.5" role="tablist" aria-label="وضع البحث">
              <button
                onClick={() => setMode("search")}
                aria-pressed={mode === "search"}
                className={`flex h-7 items-center gap-1.5 rounded-full px-2.5 text-[12.5px] transition-colors duration-150 ${
                  mode === "search"
                    ? "bg-[var(--raise)] text-[var(--ink)]"
                    : "text-[var(--muted)] hover:text-[var(--ink)]"
                }`}
              >
                <Search size={12.5} strokeWidth={1.7} />
                البحث في النصوص
              </button>
              <button
                onClick={() => setMode("ask")}
                aria-pressed={mode === "ask"}
                className={`flex h-7 items-center gap-1.5 rounded-full px-2.5 text-[12.5px] transition-colors duration-150 ${
                  mode === "ask"
                    ? "bg-[var(--raise)] text-[var(--ink)]"
                    : "text-[var(--muted)] hover:text-[var(--ink)]"
                }`}
              >
                <Sparkles size={12.5} strokeWidth={1.7} />
                اسأل المصادر
              </button>
            </div>
            <div className="relative">
              <button
                onClick={() => setFiltersOpen((open) => !open)}
                aria-expanded={filtersOpen}
                aria-label="الفلاتر"
                className={`flex h-8 items-center gap-1.5 rounded-full px-2.5 text-[12.5px] transition-colors duration-150 ${
                  filtersOpen || activeTokens.length > 0
                    ? "text-[var(--ink)]"
                    : "text-[var(--muted)] hover:bg-[var(--stone)] hover:text-[var(--ink)]"
                }`}
              >
                <SlidersHorizontal size={13} strokeWidth={1.7} />
                <span className="hidden sm:inline">فلاتر</span>
              </button>
              {filtersOpen ? (
                <FilterPopover
                  meta={metaLoaded ? meta : null}
                  filters={filters}
                  onChange={setFilters}
                  onClose={() => setFiltersOpen(false)}
                />
              ) : null}
            </div>
          </div>
          <button
            onClick={submit}
            disabled={!query.trim()}
            aria-label="إرسال"
            className="grid size-8 shrink-0 place-items-center rounded-full bg-[var(--ink)] text-[var(--paper)] transition-opacity duration-150 hover:opacity-85 disabled:opacity-25"
          >
            <ArrowUp size={15} strokeWidth={2} />
          </button>
        </div>
      </div>

      {suggestions && suggestions.length > 0 ? (
        <div className="mt-3 flex flex-wrap justify-center gap-1.5">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => {
                setQuery(suggestion);
                textareaRef.current?.focus();
              }}
              className="h-8 rounded-full border border-[var(--line)] bg-[var(--paper)] px-3 text-[12.5px] text-[var(--muted)] transition-colors duration-150 hover:border-[var(--line-strong)] hover:text-[var(--ink)]"
            >
              {suggestion}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
