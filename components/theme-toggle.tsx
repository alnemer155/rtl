"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("masadir-theme", next ? "dark" : "light");
    } catch {
      // تفضيل محلي اختياري فقط
    }
  };

  return (
    <button
      onClick={toggle}
      aria-label="تبديل الوضع الليلي"
      className="grid size-8 place-items-center rounded-full text-[var(--muted-foreground)] transition-colors duration-150 hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
    >
      {mounted && dark ? <Sun size={15} strokeWidth={1.6} /> : <Moon size={15} strokeWidth={1.6} />}
    </button>
  );
}
