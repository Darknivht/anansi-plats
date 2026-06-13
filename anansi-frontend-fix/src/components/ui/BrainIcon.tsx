"use client";

import { cn } from "../../lib/utils";
import { Brain } from "lucide-react";

interface BrainIconProps {
  size?: number;
  className?: string;
  /**
   * Whether the brain icon shows an active pulsing state.
   * Used when AI is processing or thinking.
   */
  active?: boolean;
  /**
   * Glow color when active
   */
  glow?: "amber" | "violet" | "teal";
  onClick?: () => void;
}

const glowStyles = {
  amber: "drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]",
  violet: "drop-shadow-[0_0_8px_rgba(139,92,246,0.5)]",
  teal: "drop-shadow-[0_0_8px_rgba(20,184,166,0.5)]",
};

/**
 * Animated brain icon that pulses when active.
 * Represents the Second Brain / AI state.
 */
export function BrainIcon({
  size = 24,
  className,
  active = false,
  glow = "amber",
  onClick,
}: BrainIconProps) {
  return (
    <button
      type="button"
      className={cn(
        "relative inline-flex items-center justify-center rounded-full",
        "transition-all duration-200 ease-anansi",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500",
        onClick && "cursor-pointer hover:scale-110",
        active && glowStyles[glow],
        active && "animate-brain-pulse",
        className,
      )}
      onClick={onClick}
      aria-label={active ? "AI is processing" : "Second Brain"}
      aria-busy={active}
    >
      <Brain
        size={size}
        className={cn(
          "transition-colors duration-200",
          active ? "text-brand-amber-light" : "text-[var(--color-text-muted)]",
        )}
      />
    </button>
  );
}
