"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  MessageSquarePlus,
  PanelRightClose,
  PanelRightOpen,
  Search as SearchIcon,
  Trash2,
} from "lucide-react";
import { api, type ConversationSummary } from "@/lib/api";
import { ThemeToggle } from "@/components/theme-toggle";

/**
 * App Shell: Sidebar هادئ قابل للطي + منطقة المحادثة.
 * Sidebar: محادثة جديدة، بحث في المحادثات، محادثات مجمعة بالتاريخ،
 * وفي الأسفل المكتبة والبحث والإعدادات — عناصر icon+label فقط.
 */

const DAY = 86_400_000;

function dateGroup(updatedAt: string | null): string {
  if (!updatedAt) return "أقدم";
  const age = Date.now() - new Date(updatedAt).getTime();
  if (age < DAY) return "اليوم";
  if (age < 2 * DAY) return "أمس";
  if (age < 7 * DAY) return "آخر 7 أيام";
  return "أقدم";
}

const GROUP_ORDER = ["اليوم", "أمس", "آخر 7 أيام", "أقدم"] as const;

function SidebarContent({
  collapsed,
  onToggle,
  onClose,
}: {
  collapsed: boolean;
  onToggle: () => void;
  onClose?: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  const refresh = useCallback(() => {
    api
      .conversations()
      .then(setConversations)
      .catch(() => setConversations([]));
  }, []);

  useEffect(refresh, [refresh, pathname]);

  useEffect(() => {
    const onChanged = () => refresh();
    window.addEventListener("masadir:conversations-changed", onChanged);
    return () => window.removeEventListener("masadir:conversations-changed", onChanged);
  }, [refresh]);

  useEffect(() => {
    onClose?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const remove = async (id: string) => {
    try {
      await api.deleteConversation(id);
    } catch {
      // فشل الحذف لا يكسر الواجهة
    }
    refresh();
    if (pathname === `/chat/${id}`) router.push("/");
  };

  const grouped = useMemo(() => {
    const needle = query.trim();
    const filtered = (conversations ?? []).filter((conversation) =>
      needle ? conversation.title.includes(needle) : true,
    );
    const groups = new Map<string, ConversationSummary[]>();
    for (const conversation of filtered) {
      const group = dateGroup(conversation.updated_at);
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group)!.push(conversation);
    }
    return GROUP_ORDER.filter((group) => groups.has(group)).map((group) => ({
      group,
      items: groups.get(group)!,
    }));
  }, [conversations, query]);

  const navItems = [
    { href: "/books", label: "المكتبة", icon: BookOpen },
    { href: "/search", label: "البحث في المصادر", icon: SearchIcon },
  ];

  const isChat = pathname === "/" || pathname.startsWith("/chat/");

  return (
    <div className="flex h-full flex-col rounded-2xl bg-[var(--sidebar)] p-2.5">
      <div className={`flex items-center pb-3 pt-1 ${collapsed ? "justify-center" : "justify-between px-1.5"}`}>
        {collapsed ? (
          <button
            onClick={onToggle}
            aria-label="توسيع القائمة"
            className="grid size-8 place-items-center rounded-lg text-[var(--muted-foreground)] transition-colors duration-150 hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]"
          >
            <PanelRightOpen size={16} strokeWidth={1.6} className="rtl:-scale-x-100" />
          </button>
        ) : (
          <>
            <Link href="/" className="text-[15px] font-medium tracking-tight text-[var(--foreground)]">
              مصادر
            </Link>
            <button
              onClick={onToggle}
              aria-label="طي القائمة"
              className="grid size-7 place-items-center rounded-lg text-[var(--muted-foreground)] transition-colors duration-150 hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]"
            >
              <PanelRightClose size={15} strokeWidth={1.6} className="rtl:-scale-x-100" />
            </button>
          </>
        )}
      </div>

      <Link
        href="/"
        title="محادثة جديدة"
        className={`flex h-10 items-center gap-2.5 rounded-xl px-2.5 text-[13.5px] transition-colors duration-150 ${
          isChat
            ? "bg-[var(--surface-hover)] text-[var(--foreground)]"
            : "text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]"
        } ${collapsed ? "justify-center px-0" : ""}`}
      >
        <MessageSquarePlus size={16} strokeWidth={1.7} />
        {!collapsed ? "محادثة جديدة" : null}
      </Link>

      {!collapsed ? (
        <>
          <div className="mt-2">
            {searchOpen ? (
              <input
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onBlur={() => !query && setSearchOpen(false)}
                placeholder="ابحث في المحادثات…"
                aria-label="بحث في المحادثات"
                className="h-10 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 text-[13px] text-[var(--foreground)] outline-none transition-colors duration-150 placeholder:text-[var(--muted-foreground)] focus:border-[var(--border-strong)]"
              />
            ) : (
              <button
                onClick={() => setSearchOpen(true)}
                className="flex h-10 w-full items-center gap-2.5 rounded-xl px-2.5 text-[13.5px] text-[var(--muted)] transition-colors duration-150 hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]"
              >
                <SearchIcon size={16} strokeWidth={1.7} />
                بحث في المحادثات
              </button>
            )}
          </div>

          <div className="no-scrollbar mt-3 min-h-0 flex-1 overflow-y-auto">
            {conversations === null ? (
              <p className="quiet-dot px-2.5 py-2 text-[12px] text-[var(--muted-foreground)]">…</p>
            ) : conversations.length === 0 ? (
              <p className="px-2.5 py-2 text-[12px] leading-5 text-[var(--muted-foreground)]">
                لا توجد محادثات بعد
              </p>
            ) : (
              grouped.map(({ group, items }) => (
                <div key={group} className="mb-2">
                  <p className="px-2.5 pb-1 pt-2 text-[11px] text-[var(--muted-foreground)]">{group}</p>
                  {items.map((conversation) => (
                    <div
                      key={conversation.id}
                      className={`group flex items-center gap-1 rounded-xl px-1 transition-colors duration-150 ${
                        pathname === `/chat/${conversation.id}`
                          ? "bg-[var(--surface-hover)]"
                          : "hover:bg-[var(--surface-hover)]"
                      }`}
                    >
                      <Link
                        href={`/chat/${conversation.id}`}
                        className="min-w-0 flex-1 truncate py-2 pe-0.5 text-[13px] text-[var(--muted)] transition-colors duration-150 group-hover:text-[var(--foreground)]"
                      >
                        {conversation.title}
                      </Link>
                      <button
                        onClick={() => void remove(conversation.id)}
                        aria-label={`حذف ${conversation.title}`}
                        className="grid size-6 shrink-0 place-items-center rounded-lg text-[var(--muted-foreground)] opacity-0 transition-all duration-150 hover:bg-[var(--background)] hover:text-[var(--foreground)] group-hover:opacity-100"
                      >
                        <Trash2 size={12} strokeWidth={1.6} />
                      </button>
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>

          <div className="hairline-t mt-2 space-y-0.5 pt-2">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`flex h-10 items-center gap-2.5 rounded-xl px-2.5 text-[13.5px] transition-colors duration-150 ${
                  isActive(pathname, item.href)
                    ? "bg-[var(--surface-hover)] text-[var(--foreground)]"
                    : "text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]"
                }`}
              >
                <item.icon size={16} strokeWidth={1.7} />
                {item.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center justify-between border-t border-[var(--border)] px-2.5 pt-2.5">
            <span className="text-[11px] text-[var(--muted-foreground)]">نصوص تُعرض كما وردت</span>
            <ThemeToggle />
          </div>
        </>
      ) : null}
    </div>
  );
}

function isActive(pathname: string, href: string) {
  return pathname.startsWith(href);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem("masadir-sidebar") === "collapsed");
    } catch {
      // تفضيل محلي اختياري
    }
  }, []);

  const toggle = () => {
    setCollapsed((current) => {
      const next = !current;
      try {
        localStorage.setItem("masadir-sidebar", next ? "collapsed" : "open");
      } catch {
        // تجاهل
      }
      return next;
    });
  };

  return (
    <div className="flex min-h-dvh">
      {mobileOpen ? (
        <div
          className="fixed inset-0 z-30 bg-[var(--overlay)] lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      {/* الشريط الجانبي — عائم على الحاسوب، درج على المحمول */}
      <aside
        className={`fixed inset-y-0 start-0 z-40 w-[260px] p-2 transition-transform duration-200 lg:sticky lg:top-0 lg:h-dvh lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full rtl:translate-x-full lg:translate-x-0"
        }`}
      >
        <button
          onClick={() => setMobileOpen(false)}
          aria-label="إغلاق القائمة"
          className="absolute -end-1 top-3 z-10 hidden size-0 place-items-center lg:hidden"
        />
        <SidebarContent
          collapsed={collapsed}
          onToggle={toggle}
          onClose={() => setMobileOpen(false)}
        />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* شريط علوي للمحمول فقط */}
        <div className="sticky top-0 z-20 flex h-12 items-center gap-3 bg-[var(--background)] px-4 lg:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            aria-label="القائمة"
            className="grid size-8 place-items-center rounded-lg text-[var(--muted-foreground)] transition-colors duration-150 hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
          >
            <PanelRightOpen size={16} strokeWidth={1.6} className="rtl:-scale-x-100" />
          </button>
          <Link href="/" className="text-[14px] font-medium text-[var(--foreground)]">
            مصادر
          </Link>
        </div>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
