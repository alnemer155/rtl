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
      className="grid size-10 place-items-center rounded-full transition hover:bg-[var(--stone)]"
    >
      {mounted && dark ? <Sun size={19} strokeWidth={1.8} /> : <Moon size={19} strokeWidth={1.8} />}
    </button>
  );
}
