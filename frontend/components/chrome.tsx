"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { BookOpen, Library, Search, Sparkles } from "lucide-react";
import { api, type Madhhab, type Scholar } from "@/lib/api";
import { ThemeToggle } from "@/components/theme-toggle";

export function Header() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-1">
        <Link href="/" className="display-font text-lg font-bold tracking-tight">مصادر</Link>
        <Link href="/books" className="flex items-center gap-1.5 rounded-full border border-[var(--line)] px-3 py-1.5 text-xs font-bold hover:bg-[var(--stone)]">
          <Library size={14} strokeWidth={1.8} /> المكتبة
        </Link>
        <Link href="/ask" className="flex items-center gap-1.5 rounded-full border border-[var(--line)] px-3 py-1.5 text-xs font-bold hover:bg-[var(--stone)]">
          <Sparkles size={14} strokeWidth={1.8} /> اسأل المصادر
        </Link>
        <Link href="/admin" className="hidden items-center gap-1.5 rounded-full border border-[var(--line)] px-3 py-1.5 text-xs font-bold hover:bg-[var(--stone)] sm:flex">
          <BookOpen size={14} strokeWidth={1.8} /> الإدارة
        </Link>
      </div>
      <ThemeToggle />
    </header>
  );
}

export function SearchForm({
  initialQuery = "",
  initialMadhhab = "",
  initialScholar = "",
  initialBook = "",
  compact = false,
}: {
  initialQuery?: string;
  initialMadhhab?: string;
  initialScholar?: string;
  initialBook?: string;
  compact?: boolean;
}) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [madhhab, setMadhhab] = useState(initialMadhhab);
  const [scholar, setScholar] = useState(initialScholar);
  const [book, setBook] = useState(initialBook);
  const [madhhabs, setMadhhabs] = useState<Madhhab[]>([]);
  const [scholars, setScholars] = useState<Scholar[]>([]);
  const [books, setBooks] = useState<{ id: number; title: string }[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);

  useEffect(() => {
    Promise.all([api.madhhabs(), api.scholars(), api.books()])
      .then(([madhhabList, scholarList, bookList]) => {
        setMadhhabs(madhhabList);
        setScholars(scholarList);
        setBooks(bookList.map((item) => ({ id: item.id, title: item.title })));
      })
      .catch(() => {})
      .finally(() => setLoadingMeta(false));
  }, []);

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();
    const params = new URLSearchParams();
    if (query.trim()) params.set("q", query.trim());
    if (madhhab) params.set("madhhab", madhhab);
    if (scholar) params.set("scholar", scholar);
    if (book) params.set("book", book);
    router.push(`/search?${params.toString()}`);
  };

  const selectClass =
    "rounded-xl border border-[var(--line)] bg-transparent px-3 py-2.5 text-xs outline-none transition focus:border-[var(--clay)]";

  return (
    <form onSubmit={submit} className={compact ? "space-y-3" : "space-y-4"}>
      <div className="relative">
        <Search size={18} strokeWidth={1.8} className="pointer-events-none absolute right-5 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="ابحث في الكتب والمسائل والأحاديث..."
          aria-label="بحث"
          className={`w-full rounded-[24px] border border-[var(--line)] bg-white pl-4 pr-12 outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--clay)] shadow-[0_8px_30px_rgb(25,23,22,0.06)] dark:bg-[#211f1d] ${
            compact ? "py-3.5 text-sm" : "py-5 text-base sm:text-lg"
          }`}
        />
      </div>
      <div className={`grid gap-2 ${compact ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-4"}`}>
        <select value={madhhab} onChange={(event) => setMadhhab(event.target.value)} className={selectClass} aria-label="المذهب">
          <option value="">كل المذاهب</option>
          {madhhabs.map((item) => (
            <option key={item.key} value={item.key}>{item.name_ar}</option>
          ))}
        </select>
        <select value={scholar} onChange={(event) => setScholar(event.target.value)} className={selectClass} aria-label="المرجع">
          <option value="">كل المراجع</option>
          {scholars.map((item) => (
            <option key={item.key} value={item.key}>{item.name_ar}</option>
          ))}
        </select>
        <select value={book} onChange={(event) => setBook(event.target.value)} className={selectClass} aria-label="الكتاب">
          <option value="">كل الكتب</option>
          {books.map((item) => (
            <option key={item.id} value={item.id}>{item.title}</option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-xl bg-[var(--ink)] px-4 py-2.5 text-xs font-bold text-[var(--paper)] transition hover:opacity-85"
        >
          بحث
        </button>
      </div>
      {loadingMeta ? <p className="text-[10px] text-[var(--muted)]">جارٍ تحميل الفلاتر…</p> : null}
    </form>
  );
}
