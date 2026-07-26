import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Variorum — The memory system for software teams",
  description:
    "An AI-powered engineering knowledge layer that keeps the context around your code accurate over time.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
