"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Header } from "@/components/chrome";
import { api, type BookSummary } from "@/lib/api";

export default function BooksPage() {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.books()
      .then(setBooks)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل المكتبة"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="min-h-dvh">
      <Header />
      <div className="mx-auto w-full max-w-4xl px-4 pb-16">
        <h1 className="display-font mt-6 text-2xl font-bold">المكتبة</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">الكتب المُدرجة في قاعدة المعرفة من مصادرها الرسمية.</p>
        {loading ? (
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {[0, 1].map((index) => (
              <div key={index} className="h-28 animate-pulse rounded-2xl border border-[var(--line)] bg-[var(--stone)]" />
            ))}
          </div>
        ) : error ? (
          <div role="alert" className="app-error mt-8 rounded-xl border px-4 py-3 text-sm">{error}</div>
        ) : books.length === 0 ? (
          <p className="mt-10 text-sm text-[var(--muted)]">لم يُدرج أي كتاب بعد.</p>
        ) : (
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {books.map((book) => (
              <Link
                key={book.id}
                href={`/books/${book.id}`}
                className="rounded-2xl border border-[var(--line)] bg-white p-5 transition hover:border-[var(--clay)] dark:bg-[#1b1a18]"
              >
                <h2 className="text-base font-bold leading-7">{book.title}</h2>
                {book.scholar ? <p className="mt-1 text-xs text-[var(--muted)]">{book.scholar}</p> : null}
                <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-[var(--muted)]">
                  {book.madhhab ? <span className="source-chip"><span className="source-dot" />{book.madhhab}</span> : null}
                  <span className="source-chip"><span className="source-dot" />{book.issues_count} مسألة</span>
                  <span className="source-chip"><span className="source-dot" />{book.sections_count} قسماً</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
