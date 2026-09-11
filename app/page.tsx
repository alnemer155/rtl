import { Composer } from "@/components/composer";
import { SiteHeader } from "@/components/site-header";

const SUGGESTIONS = [
  "صيام يوم عرفة",
  "حكم ربط الكتائب",
  "زكاة الفطرة",
  "غسل يوم الجمعة",
];

/**
 * الرئيسية: فراغ أولاً — حقل السؤال هو بطل الصفحة،
 * بلا عنوان ضخم ولا فقرة تسويقية ولا شارات.
 */
export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />
      <main className="flex flex-1 flex-col items-center px-5">
        <div className="flex w-full max-w-[728px] flex-1 flex-col justify-center pb-24 pt-10 sm:pt-0">
          <p className="mb-6 hidden text-center text-[15px] font-medium text-[var(--muted)] sm:block">
            مصادر موثوقة للفقه والحديث
          </p>
          <Composer variant="hero" suggestions={SUGGESTIONS} />
        </div>
      </main>
      <footer className="pb-6 text-center text-[11.5px] text-[var(--muted)]">
        كل نصٍّ مرتبط بمصدره الرسمي كما ورد
      </footer>
    </div>
  );
}
