import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "مصادر — قاعدة المصادر الفقهية والحديثية",
  description: "منصة بحثية توحّد المصادر الفقهية والحديثية السنية والشيعية مع الاستناد إلى النصوص الأصلية.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ar" dir="rtl" suppressHydrationWarning>
      <head>
        {/* استعادة الوضع الليلي قبل الرسم حتى لا يومض المظهر الفاتح عند التحديث */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{if(localStorage.getItem("masadir-theme")==="dark")document.documentElement.classList.add("dark")}catch(e){}`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
