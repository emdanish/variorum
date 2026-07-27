import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider, THEME_INIT_SCRIPT } from "@/components/theme-provider";
import { ThemedToaster } from "@/components/themed-toaster";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

// Canonical public origin, used to resolve Open Graph / social-share URLs.
// Override with NEXT_PUBLIC_SITE_URL (e.g. a preview deploy); defaults to prod.
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://variorum.dev";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
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
    url: SITE_URL,
    siteName: "Variorum",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${mono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <ThemeProvider>
          {children}
          <ThemedToaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
