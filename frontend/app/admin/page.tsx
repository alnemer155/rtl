"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/chrome";
import { api } from "@/lib/api";

interface Stats {
  books: number;
  sections: number;
  issues: number;
  scholars: number;
  sources: number;
  madhhabs: number;
  crawl_runs_total: number;
  crawl_runs_failed: number;
  ai_answers: number;
  last_crawl: {
    id: number;
    status: string;
    pages_processed: number;
    records_created: number;
    records_updated: number;
    records_unchanged: number;
    records_failed: number;
    started_at: string | null;
    finished_at: string | null;
  } | null;
}

interface CrawlRun {
  id: number;
  status: string;
  book_id: number | null;
  pages_processed: number;
  records_created: number;
  records_failed: number;
  started_at: string | null;
  finished_at: string | null;
  errors: { url?: string; error?: string }[];
}

export default function AdminPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [runs, setRuns] = useState<CrawlRun[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.stats(), api.crawlRuns()])
      .then(([statsData, runsData]) => {
        setStats(statsData);
        setRuns(runsData);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل لوحة الإدارة"));
  }, []);

  const cards: { label: string; value: number | string | undefined }[] = stats
    ? [
        { label: "المذاهب", value: stats.madhhabs },
        { label: "المصادر", value: stats.sources },
        { label: "المراجع", value: stats.scholars },
        { label: "الكتب", value: stats.books },
        { label: "الأقسام", value: stats.sections },
        { label: "المسائل", value: stats.issues },
        { label: "تشغيلات الزحف", value: stats.crawl_runs_total },
        { label: "تشغيلات فاشلة/جزئية", value: stats.crawl_runs_failed },
        { label: "أجوبة الذكاء الاصطناعي", value: stats.ai_answers },
      ]
    : [];

  return (
    <main className="min-h-dvh">
      <Header />
      <div className="mx-auto w-full max-w-4xl px-4 pb-16">
        <h1 className="display-font mt-6 text-2xl font-bold">لوحة الإدارة</h1>
        {error ? <div role="alert" className="app-error mt-6 rounded-xl border px-4 py-3 text-sm">{error}</div> : null}
        {stats ? (
          <>
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {cards.map((card) => (
                <div key={card.label} className="rounded-2xl border border-[var(--line)] bg-white p-4 dark:bg-[#1b1a18]">
                  <p className="text-2xl font-bold">{card.value}</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">{card.label}</p>
                </div>
              ))}
            </div>
            {stats.last_crawl ? (
              <section className="mt-8">
                <h2 className="text-sm font-bold">آخر تشغيلة زحف</h2>
                <div className="mt-3 rounded-2xl border border-[var(--line)] bg-white p-5 text-xs leading-7 dark:bg-[#1b1a18]">
                  <p>الحالة: <span className="font-bold">{stats.last_crawl.status}</span></p>
                  <p>صفحات معالجة: {stats.last_crawl.pages_processed}</p>
                  <p>سجلات جديدة: {stats.last_crawl.records_created} — محدثة: {stats.last_crawl.records_updated} — دون تغيير: {stats.last_crawl.records_unchanged} — فاشلة: {stats.last_crawl.records_failed}</p>
                  <p className="text-[var(--muted)]">
                    {stats.last_crawl.started_at ? new Date(stats.last_crawl.started_at).toLocaleString("ar") : ""} ← {stats.last_crawl.finished_at ? new Date(stats.last_crawl.finished_at).toLocaleString("ar") : "مستمرة"}
                  </p>
                </div>
              </section>
            ) : null}
            <section className="mt-8">
              <h2 className="text-sm font-bold">سجل التشغيلات</h2>
              <div className="mt-3 space-y-2">
                {runs.map((run) => (
                  <details key={run.id} className="rounded-xl border border-[var(--line)] bg-white p-4 text-xs dark:bg-[#1b1a18]">
                    <summary className="cursor-pointer font-bold">
                      تشغيلة #{run.id} — {run.status} — صفحات: {run.pages_processed} — سجلات: {run.records_created}
                      {run.records_failed > 0 ? ` — فاشلة: ${run.records_failed}` : ""}
                    </summary>
                    {run.errors.length > 0 ? (
                      <ul className="mt-3 space-y-1 text-[11px] text-[var(--muted)]">
                        {run.errors.map((item, index) => (
                          <li key={index} dir="ltr" className="truncate">{item.url}: {item.error}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-3 text-[11px] text-[var(--muted)]">لا أخطاء مسجلة.</p>
                    )}
                  </details>
                ))}
                {runs.length === 0 ? <p className="text-xs text-[var(--muted)]">لا تشغيلات بعد.</p> : null}
              </div>
            </section>
          </>
        ) : !error ? (
          <div className="mt-8 animate-pulse space-y-3">
            <div className="h-20 w-full rounded bg-[var(--stone)]" />
            <div className="h-20 w-full rounded bg-[var(--stone)]" />
          </div>
        ) : null}
      </div>
    </main>
  );
}
