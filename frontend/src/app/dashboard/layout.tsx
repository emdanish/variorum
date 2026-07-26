"use client";

import { DashboardChrome } from "@/components/dashboard/chrome";
import { DashboardProvider } from "@/components/dashboard/provider";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardProvider>
      <DashboardChrome>{children}</DashboardChrome>
    </DashboardProvider>
  );
}
