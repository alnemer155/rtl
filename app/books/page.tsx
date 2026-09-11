"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { SiteHeader } from "@/components/site-header";
import { api, type BookSummary } from "@/lib/api";

/**
 * المكتبة: واجهة تصفح معرفية — قائمة نظيفة عالية الكثافة،
 * البحث نصي خفيف في الأعلى والتصنيفات كسطر هادئ.
 */
export default function BooksPage() {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [madhhabKey, setMadhhabKey] = useState<string>("all");
  const [madhhabs, setMadhhabs] = useState<{ key: string; name_ar: string }[]>([]);

  useEffect(() => {
    Promise.all([api.books(), api.madhhabs()])
      .then(([bookList, madhhabList]) => {
        setBooks(bookList);
        setMadhhabs(madhhabList.map((item) => ({ key: item.key, name_ar: item.name_ar })));
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل المكتبة"))
      .finally(() => setLoading(false));
  }, []);

  const madhhabName = useCallback(
    (key: string) => madhhabs.find((item) => item.key === key)?.name_ar ?? key,
    [madhhabs],
  );

  const visible = useMemo(() => {
    const needle = query.trim();
    return books.filter((book) => {
      if (needle && !`${book.title} ${book.scholar ?? ""}`.includes(needle)) return false;
      if (madhhabKey !== "all" && book.madhhab !== madhhabName(madhhabKey)) return false;
      return true;
    });
  }, [books, query, madhhabKey, madhhabName]);

  return (
    <div className="min-h-dvh">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl px-5 pb-20 sm:px-6">
        <h1 className="pt-10 text-[20px] font-bold leading-7 text-[var(--ink)]">المكتبة</h1>

        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="ابحث في الكتب المدرجة…"
          aria-label="بحث في الكتب"
          className="mt-5 w-full rounded-full border border-[var(--line)] bg-[var(--raise)] px-4 py-2.5 text-[14px] text-[var(--ink)] outline-none transition-colors duration-200 placeholder:text-[var(--muted)] focus:border-[var(--line-strong)]"
        />

        {madhhabs.length > 1 ? (
          <div className="mt-3 flex items-center gap-4 text-[12.5px]">
            <button
              onClick={() => setMadhhabKey("all")}
              aria-pressed={madhhabKey === "all"}
              className={`transition-colors duration-150 ${
                madhhabKey === "all"
                  ? "text-[var(--ink)]"
                  : "text-[var(--muted)] hover:text-[var(--ink)]"
              }`}
            >
              الكل
            </button>
            {madhhabs.map((item) => (
              <button
                key={item.key}
                onClick={() => setMadhhabKey(item.key)}
                aria-pressed={madhhabKey === item.key}
                className={`transition-colors duration-150 ${
                  madhhabKey === item.key
                    ? "text-[var(--ink)]"
                    : "text-[var(--muted)] hover:text-[var(--ink)]"
                }`}
              >
                {item.name_ar}
              </button>
            ))}
          </div>
        ) : null}

        {loading ? (
          <p className="quiet-dot mt-12 text-[13px] text-[var(--muted)]">…</p>
        ) : error ? (
          <div role="alert" className="fade-in mt-10 text-[14px] text-[var(--muted-strong)]">
            {error}
          </div>
        ) : visible.length === 0 ? (
          <p className="fade-in mt-14 text-center text-[14px] text-[var(--muted)]">
            لا كتب مطابقة بعد.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-[var(--line)]">
            {visible.map((book) => (
              <li key={book.id} className="fade-in">
                <Link
                  href={`/books/${book.id}`}
                  className="group -mx-3 block rounded-xl px-3 py-4 transition-colors duration-150 hover:bg-[var(--stone)]"
                >
                  <h2 className="text-[15px] font-medium leading-6 text-[var(--ink)]">{book.title}</h2>
                  <p className="mt-1 text-[12.5px] text-[var(--muted)]">
                    {[book.scholar, book.madhhab, `${book.issues_count} مسألة`, `${book.sections_count} قسماً`]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
