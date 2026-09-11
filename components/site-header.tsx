"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";

/**
 * ترويسة هادئة: اسم «مصادر» + روابط نصية بسيطة + مفتاح السمة.
 * لا أزرار محاطة بحدود ولا شريط لوحة تحكم — نصوص تكتفي بنفسها.
 */
export function SiteHeader() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const links = [
    { href: "/books", label: "المكتبة" },
    { href: "/ask", label: "اسأل المصادر" },
  ];

  return (
    <header className="mx-auto flex h-14 w-full max-w-3xl items-center justify-between px-5 sm:px-6">
      <div className="flex items-center gap-5">
        <Link
          href="/"
          className="text-[15px] font-bold tracking-tight text-[var(--ink)] transition-colors duration-150 hover:text-[var(--muted-strong)]"
        >
          مصادر
        </Link>
        <nav className="hidden items-center gap-4 sm:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-[13.5px] transition-colors duration-150 ${
                pathname.startsWith(link.href)
                  ? "text-[var(--ink)]"
                  : "text-[var(--muted)] hover:text-[var(--ink)]"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-1">
        <ThemeToggle />
        <button
          onClick={() => setMenuOpen((open) => !open)}
          aria-label="القائمة"
          className="grid size-8 place-items-center rounded-full text-[var(--muted)] transition-colors duration-150 hover:bg-[var(--stone)] hover:text-[var(--ink)] sm:hidden"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M2.5 5h11M2.5 8h11M2.5 11h11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
        </button>
      </div>
      {menuOpen ? (
        <div className="fixed inset-0 z-30 sm:hidden" onClick={() => setMenuOpen(false)}>
          <div className="fade-in absolute inset-x-4 top-14 rounded-2xl border border-[var(--line)] bg-[var(--raise)] p-2">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className="block rounded-xl px-3 py-2.5 text-[14px] text-[var(--ink)] transition-colors duration-150 hover:bg-[var(--stone)]"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </header>
  );
}
