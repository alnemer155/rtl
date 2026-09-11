"use client";

import Link from "next/link";
import { ArrowUpLeft } from "lucide-react";
import type { SearchHit } from "@/lib/api";

function Snippet({ snippet }: { snippet: string }) {
  // المقتطف يأتي من الخادم بعلامات <mark> — نعرضها بأمان بعد التنقية الصارمة
  const parts = snippet.split(/(<mark>|<\/mark>)/g);
  let inside = false;
  return (
    <p className="mt-1.5 text-[14.5px] leading-[1.85] text-[var(--muted-strong)]">
      {parts.map((part, index) => {
        if (part === "<mark>") {
          inside = true;
          return null;
        }
        if (part === "</mark>") {
          inside = false;
          return null;
        }
        if (part.startsWith("<")) return null;
        return inside ? (
          <mark key={index}>{part}</mark>
        ) : (
          <span key={index}>{part}</span>
        );
      })}
    </p>
  );
}

export function SearchResults({ hits }: { hits: SearchHit[] }) {
  return (
    <div className="divide-y divide-[var(--line)]">
      {hits.map((hit) => (
        <article key={hit.issue.id} className="fade-in py-5 first:pt-1">
          <h3 className="text-[15px] font-medium leading-6">
            <Link
              href={`/issue/${hit.issue.id}`}
              className="text-[var(--ink)] transition-colors duration-150 hover:text-[var(--accent)]"
            >
              {hit.issue.issue_number !== null ? `المسألة ${hit.issue.issue_number}` : "نص من الكتاب"}
            </Link>
          </h3>
          <Snippet snippet={hit.snippet} />
          <div className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-[var(--muted)]">
            <Link
              href={`/issue/${hit.issue.id}`}
              className="transition-colors duration-150 hover:text-[var(--ink)]"
            >
              {hit.issue.book_title}
            </Link>
            {hit.issue.section_path ? (
              <>
                <span aria-hidden="true" className="opacity-50">
                  ·
                </span>
                <span className="truncate">{hit.issue.section_path}</span>
              </>
            ) : null}
            {hit.issue.scholar ? (
              <>
                <span aria-hidden="true" className="opacity-50">
                  ·
                </span>
                <span>{hit.issue.scholar}</span>
              </>
            ) : null}
            <a
              href={hit.issue.source_url}
              target="_blank"
              rel="noreferrer"
              className="ms-auto inline-flex items-center gap-1 transition-colors duration-150 hover:text-[var(--ink)]"
            >
              المصدر <ArrowUpLeft size={11} strokeWidth={1.8} />
            </a>
          </div>
        </article>
      ))}
    </div>
  );
}
