import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cashlytics",
  description: "Track, analyze, and optimize your finances in one place.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen">{children}</body>
    </html>
  );
}
