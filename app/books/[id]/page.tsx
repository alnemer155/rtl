"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowUpLeft, ChevronDown } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { api, type BookSummary, type Issue, type SectionNode } from "@/lib/api";

function TreeNode({
  node,
  selectedId,
  onSelect,
}: {
  node: SectionNode;
  selectedId: number | null;
  onSelect: (node: SectionNode) => void;
}) {
  const hasChildren = node.children.length > 0;
  const [open, setOpen] = useState(node.depth === 0);
  return (
    <li>
      <div
        className={`group flex items-center gap-1 rounded-lg py-1.5 pe-1 transition-colors duration-150 ${
          selectedId === node.id ? "bg-[var(--stone)]" : "hover:bg-[var(--stone)]"
        }`}
        style={{ marginInlineStart: `${node.depth * 14}px` }}
      >
        {hasChildren ? (
          <button
            onClick={() => setOpen((value) => !value)}
            aria-label={open ? "طي" : "توسيع"}
            aria-expanded={open}
            className="grid size-5 shrink-0 place-items-center rounded text-[var(--muted)] transition-colors duration-150 hover:text-[var(--ink)]"
          >
            <ChevronDown
              size={12}
              strokeWidth={1.7}
              className={`transition-transform duration-200 ${open ? "" : "-rotate-90 rtl:rotate-90"}`}
            />
          </button>
        ) : (
          <span className="size-5 shrink-0" />
        )}
        <button
          onClick={() => onSelect(node)}
          className={`min-w-0 flex-1 truncate text-start text-[13.5px] leading-6 transition-colors duration-150 ${
            selectedId === node.id
              ? "text-[var(--ink)]"
              : "text-[var(--muted-strong)] group-hover:text-[var(--ink)]"
          }`}
          title={node.title}
        >
          {node.title.split("»").slice(-1)[0].trim()}
        </button>
        {node.issue_count > 0 ? (
          <span className="shrink-0 text-[10.5px] tabular-nums text-[var(--muted)]">
            {node.issue_count}
          </span>
        ) : null}
      </div>
      {hasChildren && open ? (
        <ul>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} selectedId={selectedId} onSelect={onSelect} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function ReadingPane({ section }: { section: SectionNode }) {
  const [issues, setIssues] = useState<Issue[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setIssues(null);
    setError("");
    api
      .search({ section: section.id, page_size: 50 })
      .then((data) => setIssues(data.results.map((hit) => hit.issue)))
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل النصوص"));
  }, [section.id]);

  return (
    <article className="fade-in min-w-0">
      <h2 className="text-[15px] font-medium leading-6 text-[var(--ink)]">
        {section.title.split("»").slice(-1)[0].trim()}
      </h2>
      {error ? (
        <p role="alert" className="mt-4 text-[13.5px] text-[var(--muted-strong)]">
          {error}
        </p>
      ) : issues === null ? (
        <p className="quiet-dot mt-6 text-[13px] text-[var(--muted)]">…</p>
      ) : issues.length === 0 ? (
        <p className="mt-6 text-[13.5px] text-[var(--muted)]">لا نصوص مسجلة في هذا القسم بعد.</p>
      ) : (
        <div className="divide-y divide-[var(--line)]">
          {issues.map((issue) => (
            <div key={issue.id} className="py-5">
              {issue.issue_number !== null ? (
                <h3 className="mb-1.5 text-[13px] font-medium text-[var(--muted)]">
                  المسألة {issue.issue_number}
                </h3>
              ) : null}
              <p className="reading whitespace-pre-wrap">{issue.text_original}</p>
              <div className="mt-3 flex items-center gap-4 text-[12.5px]">
                <Link
                  href={`/issue/${issue.id}`}
                  className="text-[var(--muted)] underline-offset-4 transition-colors duration-150 hover:text-[var(--ink)] hover:underline"
                >
                  المسألة كاملة
                </Link>
                <a
                  href={issue.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[var(--muted)] transition-colors duration-150 hover:text-[var(--ink)]"
                >
                  المصدر <ArrowUpLeft size={11} strokeWidth={1.8} />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

export default function BookPage() {
  const params = useParams<{ id: string }>();
  const [book, setBook] = useState<BookSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<SectionNode | null>(null);

  useEffect(() => {
    if (!params?.id) return;
    setLoading(true);
    api
      .book(params.id)
      .then(setBook)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "تعذر تحميل الكتاب"))
      .finally(() => setLoading(false));
  }, [params?.id]);

  const selectSection = (node: SectionNode) => {
    setSelected(node);
    document.getElementById("reading-pane")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

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
        ) : book ? (
          <>
            <header className="pt-10">
              <h1 className="text-[20px] font-bold leading-8 text-[var(--ink)]">{book.title}</h1>
              <p className="mt-1.5 flex flex-wrap items-center gap-x-2 text-[12.5px] text-[var(--muted)]">
                {book.scholar ? <span>{book.scholar}</span> : null}
                {book.madhhab ? (
                  <>
                    <span aria-hidden="true" className="opacity-50">·</span>
                    <span>{book.madhhab}</span>
                  </>
                ) : null}
                <span aria-hidden="true" className="opacity-50">·</span>
                <span>{book.issues_count} مسألة</span>
                <a
                  href={book.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 transition-colors duration-150 hover:text-[var(--ink)]"
                >
                  المصدر الرسمي <ArrowUpLeft size={11} strokeWidth={1.8} />
                </a>
              </p>
            </header>

            <div className="mt-8 lg:grid lg:grid-cols-[260px_minmax(0,1fr)] lg:gap-8">
              <nav aria-label="فهرس الكتاب" className="lg:max-h-[70dvh] lg:overflow-y-auto lg:pe-2">
                <ul>
                  {(book.toc || []).map((node) => (
                    <TreeNode
                      key={node.id}
                      node={node}
                      selectedId={selected?.id ?? null}
                      onSelect={selectSection}
                    />
                  ))}
                </ul>
              </nav>
              <div id="reading-pane" className="mt-8 lg:mt-0 lg:border-s lg:border-[var(--line)] lg:ps-8 lg:pt-1">
                {selected ? (
                  <ReadingPane section={selected} />
                ) : (
                  <p className="text-[13.5px] leading-7 text-[var(--muted)]">
                    اختر باباً أو فصلاً من الفهرس لعرض نصوصه.
                  </p>
                )}
              </div>
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
