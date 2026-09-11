"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, ExternalLink } from "lucide-react";
import { Header } from "@/components/chrome";
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
    <main className="min-h-dvh">
      <Header />
      <div className="mx-auto w-full max-w-3xl px-4 pb-16">
        {loading ? (
          <div className="mt-10 animate-pulse space-y-3">
            <div className="h-4 w-48 rounded bg-[var(--stone)]" />
            <div className="h-32 w-full rounded bg-[var(--stone)]" />
          </div>
        ) : error ? (
          <div role="alert" className="app-error mt-10 rounded-xl border px-4 py-3 text-sm">{error}</div>
        ) : issue ? (
          <article className="mt-6">
            <Link href={`/books/${issue.book_id}`} className="flex w-fit items-center gap-1 text-xs text-[var(--muted)] transition hover:text-[var(--ink)]">
              <ArrowRight size={14} /> كتاب: {issue.book_title}
            </Link>
            <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px] text-[var(--muted)]">
              {issue.madhhab ? <span className="source-chip"><span className="source-dot" />{issue.madhhab}</span> : null}
              {issue.school ? <span className="source-chip"><span className="source-dot" />{issue.school}</span> : null}
              {issue.scholar ? <span className="source-chip"><span className="source-dot" />{issue.scholar}</span> : null}
              {issue.issue_number !== null ? (
                <span className="source-chip"><span className="source-dot" />المسألة {issue.issue_number}</span>
              ) : (
                <span className="source-chip"><span className="source-dot" />نص بلا رقم مسألة</span>
              )}
            </div>
            {issue.section_path ? (
              <nav aria-label="الموقع في الكتاب" className="mt-5 text-xs leading-6 text-[var(--muted)]">
                {issue.section_path.split(" ← ").map((part, index, all) => (
                  <span key={index}>
                    <span className={index === all.length - 1 ? "font-bold text-[var(--ink)]" : ""}>{part}</span>
                    {index < all.length - 1 ? <span className="mx-1.5">←</span> : null}
                  </span>
                ))}
              </nav>
            ) : null}
            <h1 className="display-font mt-3 text-2xl font-bold">
              {issue.issue_number !== null ? `المسألة ${issue.issue_number}` : "نص من الكتاب"}
            </h1>
            <div className="mt-5 rounded-2xl border border-[var(--line)] bg-white p-6 dark:bg-[#1b1a18]">
              <p className="whitespace-pre-wrap text-[15px] leading-9">{issue.text_original}</p>
            </div>
            <dl className="mt-6 space-y-2 rounded-2xl border border-[var(--line)] p-5 text-xs text-[var(--muted)]">
              <div className="flex gap-2">
                <dt className="font-bold text-[var(--ink)]">المصدر الرسمي:</dt>
                <dd>
                  <a href={issue.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline underline-offset-4">
                    فتح الرابط الأصلي <ExternalLink size={12} />
                  </a>
                </dd>
              </div>
              <div className="flex gap-2">
                <dt className="font-bold text-[var(--ink)]">آخر تحقق:</dt>
                <dd>{issue.verified_at ? new Date(issue.verified_at).toLocaleDateString("ar") : "لم يُتحقق يدوياً بعد"}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="font-bold text-[var(--ink)]">بصمة النص:</dt>
                <dd dir="ltr" className="font-mono text-[10px]">{issue.content_hash.slice(0, 16)}…</dd>
              </div>
              <div className="flex gap-2">
                <dt className="font-bold text-[var(--ink)]">نسخة المصدر:</dt>
                <dd>{issue.source_revision}</dd>
              </div>
            </dl>
          </article>
        ) : null}
      </div>
    </main>
  );
}
