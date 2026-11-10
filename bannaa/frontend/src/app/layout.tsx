import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "بنّاء",
  description: "منصة تطوير بالذكاء الاصطناعي: محرر، Agent، ومعاينة مباشرة",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
