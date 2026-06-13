"use client";

import { cn } from "../../lib/utils";
import { SidebarItem } from "./SidebarItem";
import { useUIStore } from "../../stores/ui";
import {
  LayoutDashboard,
  MessageCircle,
  Brain,
  GitBranch,
  Puzzle,
  Store,
  Settings,
  Users,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";

interface SidebarProps {
  className?: string;
}

const mainNavItems = [
  { href: "/app/dashboard", icon: <LayoutDashboard className="h-5 w-5" />, label: "Dashboard" },
  { href: "/app/chat", icon: <MessageCircle className="h-5 w-5" />, label: "AI Chat" },
];

const brainNavItems = [
  { href: "/app/brain", icon: <Brain className="h-5 w-5" />, label: "Overview" },
  { href: "/app/brain/graph", icon: <GitBranch className="h-5 w-5" />, label: "Graph View" },
  { href: "/app/brain/nodes", icon: <Sparkles className="h-5 w-5" />, label: "Memory Library" },
];

const secondaryNavItems = [
  { href: "/app/agents", icon: <Puzzle className="h-5 w-5" />, label: "Agents", count: 3 },
  { href: "/app/integrations", icon: <Users className="h-5 w-5" />, label: "Integrations" },
  { href: "/app/marketplace", icon: <Store className="h-5 w-5" />, label: "Marketplace" },
  { href: "/app/settings", icon: <Settings className="h-5 w-5" />, label: "Settings" },
];

/**
 * Animated sidebar with navigation items and Brain section highlight.
 * Supports expanded and collapsed states.
 * Responsive: collapses on mobile.
 */
export function Sidebar({ className }: SidebarProps) {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-[var(--color-bg-surface)] border-r border-[var(--color-border-subtle)]",
        "transition-all duration-300 ease-anansi",
        sidebarOpen ? "w-60" : "w-16",
        className,
      )}
      aria-label="Main navigation"
    >
      {/* Toggle button */}
      <div className="flex items-center justify-end p-2">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
          aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          type="button"
        >
          {sidebarOpen ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1 px-2 overflow-y-auto">
        {/* Main section */}
        <div className="space-y-0.5">
          {mainNavItems.map((item) => (
            <SidebarItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              expanded={sidebarOpen}
            />
          ))}
        </div>

        {/* Brain Section — Divider */}
        {sidebarOpen && (
          <div className="mt-4 mb-2 px-3">
            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-gradient-to-r from-amber-500/20 to-transparent" />
              <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-500/60">
                🧠 Brain
              </span>
              <div className="h-px flex-1 bg-gradient-to-l from-amber-500/20 to-transparent" />
            </div>
          </div>
        )}

        {!sidebarOpen && (
          <div className="my-2 mx-auto h-px w-6 bg-amber-500/30 rounded-full" />
        )}

        {/* Brain nav items */}
        <div className="space-y-0.5">
          {brainNavItems.map((item) => (
            <SidebarItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              expanded={sidebarOpen}
            />
          ))}
        </div>

        {/* Secondary section */}
        <div className="mt-4 space-y-0.5">
          {secondaryNavItems.map((item) => (
            <SidebarItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              expanded={sidebarOpen}
              count={item.count}
            />
          ))}
        </div>
      </nav>
    </aside>
  );
}
