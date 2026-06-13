"use client";

import { cn } from "../../lib/utils";
import { useUIStore } from "../../stores/ui";
import { BrainIcon } from "../../components/ui/BrainIcon";
import {
  Search,
  Bell,
  Command,
  Settings,
  Menu,
  LogOut,
  User,
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";

interface TopBarProps {
  className?: string;
}

/**
 * Top bar with logo, search (Cmd+K), quick actions, and user avatar.
 * Includes command palette keyboard shortcut.
 */
export function TopBar({ className }: TopBarProps) {
  const { toggleSidebar, toggleCommandPalette, commandPaletteOpen, setCommandPaletteOpen } =
    useUIStore();
  const [notifications, setNotifications] = useState(3);

  // Cmd+K / Ctrl+K to open command palette
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        toggleCommandPalette();
      }
    },
    [toggleCommandPalette],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <header
      className={cn(
        "flex items-center justify-between h-14 px-4 border-b border-[var(--color-border-subtle)]",
        "bg-[var(--color-bg-surface)]/80 backdrop-blur-lg",
        className,
      )}
    >
      {/* Left: Menu + Logo */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors lg:hidden"
          aria-label="Toggle sidebar"
          type="button"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2">
          <BrainIcon size={20} active glow="amber" />
          <span className="text-sm font-heading font-bold text-[var(--color-text-primary)] hidden sm:inline">
            anansi
          </span>
        </div>
      </div>

      {/* Center: Search */}
      <button
        onClick={() => setCommandPaletteOpen(true)}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-lg min-w-[200px] sm:min-w-[320px]",
          "bg-[var(--glass-interactive-bg)] backdrop-blur-[16px]",
          "border border-[var(--color-border-subtle)]",
          "text-sm text-[var(--color-text-muted)]",
          "hover:border-amber-500/30 hover:text-[var(--color-text-secondary)]",
          "transition-all duration-200 ease-anansi",
        )}
        type="button"
        aria-label="Open command palette"
      >
        <Search className="h-4 w-4 shrink-0" />
        <span className="hidden sm:inline">Search memories, agents, commands...</span>
        <span className="sm:hidden">Search...</span>
        <span className="ml-auto hidden sm:flex items-center gap-0.5 text-[10px] font-mono text-[var(--color-text-disabled)] bg-white/5 rounded px-1.5 py-0.5">
          <Command className="h-3 w-3" />
          K
        </span>
      </button>

      {/* Right: Actions + Avatar */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <button
          className="relative p-2 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
          aria-label={`Notifications (${notifications} unread)`}
          type="button"
        >
          <Bell className="h-5 w-5" />
          {notifications > 0 && (
            <span className="absolute top-1 right-1 h-4 w-4 flex items-center justify-center rounded-full bg-semantic-error text-[10px] font-bold text-white">
              {notifications > 9 ? "9+" : notifications}
            </span>
          )}
        </button>

        {/* Settings */}
        <button
          className="hidden sm:flex p-2 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
          aria-label="Settings"
          type="button"
        >
          <Settings className="h-5 w-5" />
        </button>

        {/* Avatar */}
        <div className="relative group">
          <button
            className="flex items-center gap-2 p-1 rounded-lg hover:bg-white/5 transition-colors"
            aria-label="User menu"
            type="button"
          >
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brand-amber to-brand-amber-light flex items-center justify-center text-white text-sm font-semibold">
              A
            </div>
          </button>

          {/* Dropdown */}
          <div
            className={cn(
              "absolute right-0 top-full mt-1 w-48 glass-elevated rounded-lg py-1 shadow-glass-xl",
              "opacity-0 invisible group-hover:opacity-100 group-hover:visible",
              "transition-all duration-200 ease-anansi",
              "pointer-events-none group-hover:pointer-events-auto",
            )}
            role="menu"
          >
            <a
              href="/app/settings"
              className="flex items-center gap-2 px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
              role="menuitem"
            >
              <User className="h-4 w-4" />
              Profile
            </a>
            <a
              href="/app/settings"
              className="flex items-center gap-2 px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
              role="menuitem"
            >
              <Settings className="h-4 w-4" />
              Settings
            </a>
            <hr className="my-1 border-[var(--color-border-subtle)]" />
            <button
              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-semantic-error hover:bg-white/5 transition-colors"
              role="menuitem"
              type="button"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
