import { Header, SearchForm } from "@/components/chrome";

export default function Home() {
  return (
    <main className="flex min-h-dvh flex-col">
      <Header />
      <section className="flex flex-1 flex-col items-center justify-center px-4 pb-24">
        <h1 className="display-font text-4xl font-bold leading-tight sm:text-5xl">مصــادر</h1>
        <p className="mx-auto mt-4 max-w-md text-center text-sm leading-7 text-[var(--muted)]">
          قاعدة معرفية موحدة تجمع المصادر الفقهية والحديثية السنية والشيعية،
          بكل نصّ مرتبط بمصدره الرسمي وانتمائه.
        </p>
        <div className="mx-auto mt-8 w-full max-w-2xl">
          <SearchForm />
        </div>
        <div className="mt-6 flex flex-wrap justify-center gap-2 text-[11px] text-[var(--muted)]">
          <span className="source-chip"><span className="source-dot" />بحث تقليدي في النصوص</span>
          <span className="source-chip"><span className="source-dot" />فلترة بالمذهب والمرجع</span>
          <span className="source-chip"><span className="source-dot" />روابط للمصادر الأصلية</span>
        </div>
      </section>
      <footer className="pb-6 text-center text-[10px] text-[var(--muted)]">
        النصوص تُعرض كما وردت في مصادرها الرسمية دون تعديل.
      </footer>
    </main>
  );
}
