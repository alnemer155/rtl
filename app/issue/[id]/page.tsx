"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowUpLeft } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { api, type Issue } from "@/lib/api";

export default function IssuePage() {
  const params = useParams<{ id: string }>();
  const [issue, setIssue] = useState<Issue | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params?.id) return;
    setLoading(true);
    api
      .issue(params.id)
      .then(setIssue)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل المسألة"))
      .finally(() => setLoading(false));
  }, [params?.id]);

  return (
    <div className="min-h-dvh">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl px-5 pb-20 sm:px-6">
        {loading ? (
          <p className="quiet-dot pt-12 text-[13px] text-[var(--muted)]">…</p>
        ) : error ? (
          <div role="alert" className="fade-in pt-12 text-[14px] text-[var(--muted-strong)]">
            {error}
          </div>
        ) : issue ? (
          <article className="fade-in pt-10">
            {issue.section_path ? (
              <nav aria-label="الموقع في الكتاب" className="text-[12.5px] leading-6 text-[var(--muted)]">
                {issue.section_path.split(" ← ").map((part, index, all) => (
                  <span key={index}>
                    {part}
                    {index < all.length - 1 ? <span className="mx-1.5 opacity-50">←</span> : null}
                  </span>
                ))}
              </nav>
            ) : null}

            <h1 className="mt-2 text-[20px] font-bold leading-8 text-[var(--ink)]">
              {issue.issue_number !== null ? `المسألة ${issue.issue_number}` : "نص من الكتاب"}
            </h1>
            <p className="mt-1 text-[12.5px] text-[var(--muted)]">
              {[
                issue.book_title,
                issue.scholar,
                issue.madhhab,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>

            <p className="reading mt-7 whitespace-pre-wrap">{issue.text_original}</p>

            <footer className="hairline-t mt-10 flex flex-wrap items-center gap-x-5 gap-y-2 pt-4 text-[12.5px] text-[var(--muted)]">
              <a
                href={issue.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 transition-colors duration-150 hover:text-[var(--ink)]"
              >
                المصدر الأصلي <ArrowUpLeft size={11} strokeWidth={1.8} />
              </a>
              <span>
                آخر تحقق:{" "}
                {issue.verified_at
                  ? new Date(issue.verified_at).toLocaleDateString("ar")
                  : "لم يُتحقق يدوياً بعد"}
              </span>
              <span dir="ltr" className="font-mono text-[10.5px] opacity-70">
                {issue.content_hash.slice(0, 12)}…
              </span>
              <Link
                href={`/books/${issue.book_id}`}
                className="transition-colors duration-150 hover:text-[var(--ink)]"
              >
                فهرس الكتاب
              </Link>
            </footer>
          </article>
        ) : null}
      </main>
    </div>
  );
}
