"use client";

import { cn } from "@/lib/utils";
import { Link } from "lucide-react";

interface WikilinkProps {
  /**
   * The reference target (e.g., "Second Brain", "Project Alpha")
   */
  target: string;
  /**
   * Optional display label (defaults to target)
   */
  label?: string;
  onClick?: (target: string) => void;
  className?: string;
  /**
   * Whether this is a broken/unresolved link (node doesn't exist yet)
   */
  unresolved?: boolean;
}

/**
 * [[wikilink]] component that renders as a clickable pill badge.
 * Inspired by Obsidian's [[wikilink]] notation.
 * Clicking opens the memory detail view.
 */
export function Wikilink({
  target,
  label,
  onClick,
  className,
  unresolved = false,
}: WikilinkProps) {
  return (
    <button
      type="button"
      onClick={() => onClick?.(target)}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
        "transition-all duration-150 ease-anansi",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500",
        unresolved
          ? "bg-amber-500/5 text-amber-400/60 border border-amber-500/10 hover:bg-amber-500/10 hover:text-amber-400"
          : "bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 hover:border-amber-500/40 hover:shadow-glow-amber",
        "active:scale-95",
        className,
      )}
      aria-label={`Open memory: ${target}`}
      title={`Open [[${target}]]`}
    >
      <Link className="h-3 w-3 shrink-0" aria-hidden="true" />
      <span>{label ?? target}</span>
    </button>
  );
}
