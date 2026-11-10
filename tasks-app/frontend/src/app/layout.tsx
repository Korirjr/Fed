import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "مهامي",
  description: "تطبيق مهام بسيط: Next.js + Axum",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
