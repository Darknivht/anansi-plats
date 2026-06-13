"use client";

import { type ReactNode } from "react";
import { cn } from "../../lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface SidebarItemProps {
  href: string;
  icon: ReactNode;
  label: string;
  expanded: boolean;
  /**
   * Number of items in this section (for badge)
   */
  count?: number;
  /**
   * Whether this item shows an active/processing state
   */
  isActive?: boolean;
  onClick?: () => void;
}

/**
 * Individual sidebar navigation item.
 * Shows icon + label when expanded, icon-only with tooltip when collapsed.
 */
export function SidebarItem({
  href,
  icon,
  label,
  expanded,
  count,
  isActive,
  onClick,
}: SidebarItemProps) {
  const pathname = usePathname();
  const isCurrentRoute = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "group relative flex items-center gap-3 rounded-lg px-3 py-2.5",
        "transition-all duration-200 ease-anansi",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500",
        isCurrentRoute || isActive
          ? "bg-amber-500/10 text-brand-amber-light border border-amber-500/20"
          : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 border border-transparent",
      )}
      title={!expanded ? label : undefined}
      aria-label={label}
      aria-current={isCurrentRoute ? "page" : undefined}
    >
      {/* Icon */}
      <span
        className={cn(
          "shrink-0 h-5 w-5 flex items-center justify-center",
          isCurrentRoute && "text-brand-amber-light",
        )}
      >
        {icon}
      </span>

      {/* Label */}
      {expanded && (
        <span className="text-sm font-medium truncate">{label}</span>
      )}

      {/* Count badge */}
      {expanded && count !== undefined && count > 0 && (
        <span
          className={cn(
            "ml-auto inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-semibold rounded-full min-w-[18px]",
            isCurrentRoute
              ? "bg-amber-500/20 text-amber-300"
              : "bg-white/10 text-[var(--color-text-muted)]",
          )}
        >
          {count}
        </span>
      )}

      {/* Tooltip when collapsed */}
      {!expanded && (
        <span
          className={cn(
            "absolute left-full ml-2 px-2 py-1 rounded-md text-xs font-medium",
            "bg-[var(--color-surface-card)] text-[var(--color-text-primary)]",
            "border border-[var(--color-border-subtle)] shadow-glass-md",
            "opacity-0 invisible group-hover:opacity-100 group-hover:visible",
            "transition-all duration-150 ease-anansi",
            "pointer-events-none z-50 whitespace-nowrap",
          )}
          role="tooltip"
        >
          {label}
        </span>
      )}
    </Link>
  );
}
