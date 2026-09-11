"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Composer, type FilterState } from "@/components/composer";
import { SearchResults } from "@/components/search-results";
import { SiteHeader } from "@/components/site-header";
import { api, type SearchResponse } from "@/lib/api";

function parseFilters(params: URLSearchParams): FilterState {
  return {
    madhhab: params.get("madhhab") || undefined,
    scholar: params.get("scholar") || undefined,
    book: params.get("book") || undefined,
    source: params.get("source") || undefined,
  };
}

function ResultsInner() {
  const params = useSearchParams();
  const query = params.get("q") || "";
  const page = Number(params.get("page") || "1");
  const filters = parseFilters(params);

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
        source: filters.source,
      })
      .then(setData)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل النتائج"))
      .finally(() => setLoading(false));
  }, [query, page, filters.madhhab, filters.scholar, filters.book, filters.source]);

  useEffect(load, [load]);

  const goToPage = (next: number) => {
    const updated = new URLSearchParams(params.toString());
    updated.set("page", String(next));
    window.location.search = updated.toString();
  };

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <main className="mx-auto w-full max-w-3xl px-5 pb-20 sm:px-6">
      <div className="pt-8">
        <Composer
          variant="docked"
          initialQuery={query}
          initialFilters={filters}
        />
      </div>

      {loading ? (
        <div className="mt-12 space-y-1">
          {[0, 1, 2, 3].map((index) => (
            <div key={index} className="quiet-dot py-5 text-[13px] text-[var(--muted)]">
              يبحث في النصوص…
            </div>
          ))}
        </div>
      ) : error ? (
        <div role="alert" className="fade-in mt-10 text-[14px] leading-7 text-[var(--muted-strong)]">
          {error}
        </div>
      ) : !data || data.results.length === 0 ? (
        <p className="fade-in mt-14 text-center text-[14px] text-[var(--muted)]">
          {query
            ? "لا نتائج مطابقة — جرّب كلمات أقل أو أزل بعض الفلاتر."
            : "اكتب ما تبحث عنه في النصوص."}
        </p>
      ) : (
        <>
          <p className="fade-in mt-8 text-[12.5px] text-[var(--muted)]">
            {data.total} نتيجة
            {query ? (
              <>
                {" "}
                عن «<span className="text-[var(--muted-strong)]">{query}</span>»
              </>
            ) : null}
          </p>
          <div className="mt-2">
            <SearchResults hits={data.results} />
          </div>
          {totalPages > 1 ? (
            <div className="mt-8 flex items-center justify-center gap-5 text-[13px]">
              <button
                onClick={() => goToPage(data.page - 1)}
                disabled={data.page <= 1}
                aria-label="الصفحة السابقة"
                className="grid size-8 place-items-center rounded-full text-[var(--muted)] transition-colors duration-150 hover:bg-[var(--stone)] hover:text-[var(--ink)] disabled:opacity-30"
              >
                <ChevronRight size={15} />
              </button>
              <span className="tabular-nums text-[var(--muted)]">
                {data.page} / {totalPages}
              </span>
              <button
                onClick={() => goToPage(data.page + 1)}
                disabled={data.page >= totalPages}
                aria-label="الصفحة التالية"
                className="grid size-8 place-items-center rounded-full text-[var(--muted)] transition-colors duration-150 hover:bg-[var(--stone)] hover:text-[var(--ink)] disabled:opacity-30"
              >
                <ChevronLeft size={15} />
              </button>
            </div>
          ) : null}
        </>
      )}
    </main>
  );
}

export default function SearchPage() {
  return (
    <div className="min-h-dvh">
      <SiteHeader />
      <Suspense
        fallback={
          <div className="mx-auto mt-10 max-w-3xl px-5 text-[13px] text-[var(--muted)]">…</div>
        }
      >
        <ResultsInner />
      </Suspense>
    </div>
  );
}
