import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider, THEME_INIT_SCRIPT } from "@/components/theme-provider";
import { ThemedToaster } from "@/components/themed-toaster";
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
