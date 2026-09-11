"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, ExternalLink, FileText } from "lucide-react";
import { Header, SearchForm } from "@/components/chrome";
import { api, type SearchResponse } from "@/lib/api";

function Snippet({ snippet }: { snippet: string }) {
  // المقتطف يأتي من الخادم بعلامات <mark> — نعرضها بأمان بعد التنقية الصارمة
  const parts = snippet.split(/(<mark>|<\/mark>)/g);
  return (
    <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
      {parts.map((part, index) =>
        part === "<mark>" || part === "</mark>" ? null : part.startsWith("<") ? null : index > 0 && parts[index - 1] === "<mark>" ? (
          <mark key={index} className="search-highlight">{part}</mark>
        ) : (
          <span key={index}>{part}</span>
        ),
      )}
    </p>
  );
}

function ResultsInner() {
  const params = useSearchParams();
  const query = params.get("q") || "";
  const page = Number(params.get("page") || "1");
  const filters = {
    madhhab: params.get("madhhab") || undefined,
    scholar: params.get("scholar") || undefined,
    book: params.get("book") || undefined,
  };
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .search({
        q: query,
        page,
        page_size: 20,
        madhhab: filters.madhhab,
        scholar: filters.scholar,
        book: filters.book,
      })
      .then(setData)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل النتائج"))
      .finally(() => setLoading(false));
  }, [query, page, filters.madhhab, filters.scholar, filters.book]);

  useEffect(load, [load]);

  const goToPage = (next: number) => {
    const updated = new URLSearchParams(params.toString());
    updated.set("page", String(next));
    window.location.search = updated.toString();
  };

  return (
    <div className="mx-auto w-full max-w-4xl px-4 pb-16">
      <SearchForm
        compact
        initialQuery={query}
        initialMadhhab={filters.madhhab || ""}
        initialScholar={filters.scholar || ""}
        initialBook={filters.book || ""}
      />
      {loading ? (
        <div className="mt-10 space-y-4">
          {[0, 1, 2].map((index) => (
            <div key={index} className="animate-pulse rounded-2xl border border-[var(--line)] p-5">
              <div className="h-4 w-40 rounded bg-[var(--stone)]" />
              <div className="mt-3 h-3 w-full rounded bg-[var(--stone)]" />
              <div className="mt-2 h-3 w-2/3 rounded bg-[var(--stone)]" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div role="alert" className="app-error mt-8 rounded-xl border px-4 py-3 text-sm">{error}</div>
      ) : !data || data.results.length === 0 ? (
        <p className="mt-10 text-center text-sm text-[var(--muted)]">
          {query ? "لا توجد نتائج مطابقة بعد. جرّب كلمات أقل أو أزل بعض الفلاتر." : "اكتب كلمة للبحث في النصوص."}
        </p>
      ) : (
        <>
          <p className="mt-6 text-xs text-[var(--muted)]">
            {data.total} نتيجة — صفحة {data.page}
          </p>
          <div className="mt-4 space-y-4">
            {data.results.map((hit) => (
              <article key={hit.issue.id} className="rounded-2xl border border-[var(--line)] bg-white p-5 transition hover:border-[var(--clay)] dark:bg-[#1b1a18]">
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--muted)]">
                  {hit.issue.issue_number !== null ? (
                    <span className="source-chip"><span className="source-dot" />المسألة {hit.issue.issue_number}</span>
                  ) : null}
                  <span className="source-chip"><span className="source-dot" />{hit.issue.book_title}</span>
                  {hit.issue.madhhab ? <span className="source-chip"><span className="source-dot" />{hit.issue.madhhab}</span> : null}
                  {hit.issue.scholar ? <span className="source-chip"><span className="source-dot" />{hit.issue.scholar}</span> : null}
                </div>
                {hit.issue.section_path ? (
                  <p className="mt-3 text-xs font-bold text-[var(--ink)]">{hit.issue.section_path}</p>
                ) : null}
                <Snippet snippet={hit.snippet} />
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Link
                    href={`/issue/${hit.issue.id}`}
                    className="flex items-center gap-1.5 rounded-full bg-[var(--ink)] px-3.5 py-1.5 text-[11px] font-bold text-[var(--paper)] transition hover:opacity-85"
                  >
                    <FileText size={13} strokeWidth={2} /> عرض النص الكامل
                  </Link>
                  <a
                    href={hit.issue.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 rounded-full border border-[var(--line)] px-3.5 py-1.5 text-[11px] font-bold transition hover:bg-[var(--stone)]"
                  >
                    <ExternalLink size={13} strokeWidth={2} /> المصدر الأصلي
                  </a>
                </div>
              </article>
            ))}
          </div>
          {data.total > data.page_size ? (
            <div className="mt-8 flex items-center justify-center gap-4 text-xs">
              <button
                onClick={() => goToPage(data.page - 1)}
                disabled={data.page <= 1}
                className="flex items-center gap-1 rounded-full border border-[var(--line)] px-4 py-2 font-bold transition hover:bg-[var(--stone)] disabled:opacity-40"
              >
                <ChevronRight size={14} /> السابق
              </button>
              <span className="text-[var(--muted)]">
                {data.page} / {Math.ceil(data.total / data.page_size)}
              </span>
              <button
                onClick={() => goToPage(data.page + 1)}
                disabled={data.page >= Math.ceil(data.total / data.page_size)}
                className="flex items-center gap-1 rounded-full border border-[var(--line)] px-4 py-2 font-bold transition hover:bg-[var(--stone)] disabled:opacity-40"
              >
                التالي <ChevronLeft size={14} />
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <main className="min-h-dvh">
      <Header />
      <Suspense fallback={<div className="mx-auto mt-10 max-w-4xl px-4 text-sm text-[var(--muted)]">جارٍ التحميل…</div>}>
        <ResultsInner />
      </Suspense>
    </main>
  );
}
