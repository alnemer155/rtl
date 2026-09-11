"use client";

/**
 * حالة البحث: سطر صامت واحد يتغير (يبحث في المصادر… يصيغ الإجابة…)
 * مع إمكانية فتح التفاصيل في سطر واحد فقط عند الطي.
 */
export function ResearchProgress({
  lines,
  done,
}: {
  lines: string[];
  done: boolean;
}) {
  if (lines.length === 0) return null;
  const current = lines.at(-1)!;
  if (done) {
    return (
      <details className="fade-in group">
        <summary className="cursor-pointer list-none text-[12.5px] text-[var(--muted-foreground)] transition-colors duration-150 hover:text-[var(--muted)]">
          <span className="inline-block size-1.5 rounded-full bg-[var(--muted-foreground)] me-2 align-middle" />
          بحث في {lines.filter((line) => line.startsWith("يبحث")).length} مصادر
        </summary>
        <ul className="mt-1.5 space-y-1 ps-4">
          {lines.map((line, index) => (
            <li key={index} className="text-[12px] leading-5 text-[var(--muted-foreground)]">
              {line}
            </li>
          ))}
        </ul>
      </details>
    );
  }
  return (
    <p className="fade-in flex items-center gap-2 text-[13px] text-[var(--muted-foreground)]">
      <span className="quiet-dot inline-block size-1.5 rounded-full bg-[var(--muted-foreground)]" />
      {current}
    </p>
  );
}
