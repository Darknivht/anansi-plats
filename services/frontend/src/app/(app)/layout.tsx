"use client";

import { useUIStore } from "@/stores/ui";
import { TopBar } from "@/components/layout/TopBar";
import { Sidebar } from "@/components/layout/Sidebar";
import { ToastContainer } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-[var(--color-bg-deepest)]">
      {/* Toast notifications */}
      <ToastContainer />

      {/* Top Bar */}
      <TopBar />

      {/* Body: Sidebar + Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar />

        {/* Main Content */}
        <main
          className={cn(
            "flex-1 overflow-y-auto transition-all duration-300 ease-anansi",
          )}
        >
          <div className="p-6 lg:p-8 max-w-6xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
