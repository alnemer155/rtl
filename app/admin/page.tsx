"use client";

import { useEffect, useState } from "react";
import { SiteHeader } from "@/components/site-header";
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
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل اللوحة"));
  }, []);

  const cards: { label: string; value: number }[] = stats
    ? [
        { label: "الكتب", value: stats.books },
        { label: "الأقسام", value: stats.sections },
        { label: "المسائل", value: stats.issues },
        { label: "المراجع", value: stats.scholars },
        { label: "المصادر", value: stats.sources },
        { label: "تشغيلات الزحف", value: stats.crawl_runs_total },
        { label: "فاشلة/جزئية", value: stats.crawl_runs_failed },
        { label: "أجوبة الذكاء", value: stats.ai_answers },
      ]
    : [];

  return (
    <div className="min-h-dvh">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl px-5 pb-20 sm:px-6">
        <h1 className="pt-10 text-[20px] font-bold leading-7 text-[var(--ink)]">الإدارة</h1>

        {error ? (
          <div role="alert" className="fade-in mt-6 text-[14px] text-[var(--muted-strong)]">
            {error}
          </div>
        ) : null}

        {stats ? (
          <>
            <dl className="mt-6 grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
              {cards.map((card) => (
                <div key={card.label}>
                  <dt className="text-[11.5px] text-[var(--muted)]">{card.label}</dt>
                  <dd className="mt-0.5 text-[22px] font-medium tabular-nums leading-7 text-[var(--ink)]">
                    {card.value.toLocaleString("ar-EG")}
                  </dd>
                </div>
              ))}
            </dl>

            {stats.last_crawl ? (
              <section className="hairline-t mt-10 pt-6">
                <h2 className="text-[14px] font-medium text-[var(--ink)]">آخر تشغيلة زحف</h2>
                <p className="mt-2 text-[13px] leading-7 text-[var(--muted)]">
                  الحالة <span className="text-[var(--muted-strong)]">{stats.last_crawl.status}</span> ·
                  صفحات {stats.last_crawl.pages_processed} · جديدة {stats.last_crawl.records_created} ·
                  محدثة {stats.last_crawl.records_updated} · دون تغيير {stats.last_crawl.records_unchanged} ·
                  فاشلة {stats.last_crawl.records_failed}
                </p>
              </section>
            ) : null}

            <section className="hairline-t mt-10 pt-6">
              <h2 className="text-[14px] font-medium text-[var(--ink)]">سجل التشغيلات</h2>
              <ul className="mt-3 divide-y divide-[var(--line)]">
                {runs.map((run) => (
                  <li key={run.id} className="py-3.5">
                    <details className="group">
                      <summary className="flex cursor-pointer list-none items-baseline gap-3 text-[13px]">
                        <span className="text-[var(--ink)]">#{run.id}</span>
                        <span className="text-[var(--muted)]">{run.status}</span>
                        <span className="text-[var(--muted)]">
                          صفحات {run.pages_processed} · سجلات {run.records_created}
                          {run.records_failed > 0 ? ` · فاشلة ${run.records_failed}` : ""}
                        </span>
                      </summary>
                      {run.errors.length > 0 ? (
                        <ul className="mt-2 space-y-1 ps-6 text-[11.5px] leading-5 text-[var(--muted)]">
                          {run.errors.map((item, index) => (
                            <li key={index} dir="ltr" className="truncate text-start">
                              {item.url}: {item.error}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </details>
                  </li>
                ))}
                {runs.length === 0 ? (
                  <li className="py-3 text-[13px] text-[var(--muted)]">لا تشغيلات بعد.</li>
                ) : null}
              </ul>
            </section>
          </>
        ) : !error ? (
          <p className="quiet-dot pt-12 text-[13px] text-[var(--muted)]">…</p>
        ) : null}
      </main>
    </div>
  );
}
