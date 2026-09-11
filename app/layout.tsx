import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "مصادر — مساعد إسلامي قائم على المصادر",
  description:
    "Chatbot إسلامي يجيب اعتماداً على المصادر الأصلية: sistani.org والمكتبة التراثية وبحث الويب.",
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
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
