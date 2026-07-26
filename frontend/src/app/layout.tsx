import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL("http://localhost:3000"),
  title: {
    default: "Variorum — The engineering memory layer for software teams",
    template: "%s · Variorum",
  },
  description:
    "Variorum is your AI engineering memory layer. It understands your codebase, keeps documentation in sync, preserves engineering decisions, and flags risky changes — so knowledge never leaves with the people who wrote it.",
  keywords: [
    "engineering knowledge",
    "documentation drift",
    "codebase understanding",
    "developer tools",
    "GitHub app",
    "AI for engineering teams",
  ],
  openGraph: {
    title: "Variorum — The engineering memory layer for software teams",
    description:
      "Understand your codebase, keep docs in sync, and preserve engineering decisions.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        {children}
        <Toaster
          theme="dark"
          position="top-right"
          richColors
          closeButton
          toastOptions={{ classNames: { toast: "font-sans" } }}
        />
      </body>
    </html>
  );
}
