"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ChevronDown, ExternalLink } from "lucide-react";
import { Header } from "@/components/chrome";
import { api, type BookSummary, type SectionNode } from "@/lib/api";

function TreeNode({ node }: { node: SectionNode }) {
  const hasChildren = node.children.length > 0;
  const [open, setOpen] = useState(node.depth === 0);
  return (
    <li className="text-sm">
      <div className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 transition hover:bg-[var(--stone)]">
        {hasChildren ? (
          <button
            onClick={() => setOpen((value) => !value)}
            aria-label={open ? "طي" : "توسيع"}
            aria-expanded={open}
            className="grid size-5 shrink-0 place-items-center rounded transition hover:bg-[var(--line)]"
          >
            <ChevronDown size={13} className={`transition-transform ${open ? "" : "-rotate-90"}`} />
          </button>
        ) : (
          <span className="size-5 shrink-0" />
        )}
        <a href={node.source_url} target="_blank" rel="noreferrer" className="min-w-0 flex-1 truncate leading-7 hover:underline" title={node.title}>
          {node.title}
        </a>
        {node.issue_count > 0 ? (
          <span className="shrink-0 text-[10px] text-[var(--muted)]">{node.issue_count}</span>
        ) : null}
      </div>
      {hasChildren && open ? (
        <ul className="mr-5 border-r border-[var(--line)] pr-2">
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export default function BookPage() {
  const params = useParams<{ id: string }>();
  const [book, setBook] = useState<BookSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params?.id) return;
    setLoading(true);
    api.book(params.id)
      .then(setBook)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل الكتاب"))
      .finally(() => setLoading(false));
  }, [params?.id]);

  return (
    <main className="min-h-dvh">
      <Header />
      <div className="mx-auto w-full max-w-3xl px-4 pb-16">
        {loading ? (
          <div className="mt-10 animate-pulse space-y-3">
            <div className="h-6 w-64 rounded bg-[var(--stone)]" />
            <div className="h-64 w-full rounded bg-[var(--stone)]" />
          </div>
        ) : error ? (
          <div role="alert" className="app-error mt-10 rounded-xl border px-4 py-3 text-sm">{error}</div>
        ) : book ? (
          <>
            <h1 className="display-font mt-6 text-2xl font-bold leading-9">{book.title}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-[var(--muted)]">
              {book.scholar ? <span className="source-chip"><span className="source-dot" />{book.scholar}</span> : null}
              {book.madhhab ? <span className="source-chip"><span className="source-dot" />{book.madhhab}</span> : null}
              {book.school ? <span className="source-chip"><span className="source-dot" />{book.school}</span> : null}
              <span className="source-chip"><span className="source-dot" />{book.issues_count} مسألة</span>
              <span className="source-chip"><span className="source-dot" />{book.sections_count} قسماً</span>
            </div>
            <a href={book.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs text-[var(--muted)] underline underline-offset-4 hover:text-[var(--ink)]">
              المصدر الرسمي <ExternalLink size={12} />
            </a>
            <h2 className="mt-8 text-sm font-bold">فهرس الكتاب</h2>
            <ul className="mt-3 rounded-2xl border border-[var(--line)] bg-white p-4 dark:bg-[#1b1a18]">
              {(book.toc || []).map((node) => (
                <TreeNode key={node.id} node={node} />
              ))}
            </ul>
          </>
        ) : null}
      </div>
    </main>
  );
}
