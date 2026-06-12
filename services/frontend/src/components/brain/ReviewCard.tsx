"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/ui/GlassCard";
import { Badge } from "@/components/ui/Badge";
import { AnansiButton } from "@/components/ui/AnansiButton";
import {
  ChevronDown,
  ChevronUp,
  Brain,
  Clock,
  Zap,
  BarChart3,
  RotateCw,
  Layers,
} from "lucide-react";

// ─── Types ──────────────────────────────────────────────────────────────────────

interface ReviewCardProps {
  node: {
    id: string;
    title: string;
    content: string;
    layers?: Record<string, unknown>;
    tags?: string[];
    type: string;
    reviewInterval: number;
    daysSinceReview: number | null;
    recentReviews?: {
      rating: string;
      intervalBefore: number;
      intervalAfter: number;
      createdAt: string;
    }[];
    linksCount: number;
  };
  onRate: (nodeId: string, rating: "easy" | "medium" | "hard" | "forgot") => void;
  cardIndex: number;
  totalCards: number;
  isActive: boolean;
  className?: string;
}

// ─── Interval formatter ─────────────────────────────────────────────────────────

function formatInterval(seconds: number): string {
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  const days = Math.round(seconds / 86400);
  return `${days}d`;
}

// ─── Component ───────────────────────────────────────────────────────────────────

export function ReviewCard({
  node,
  onRate,
  cardIndex,
  totalCards,
  isActive,
  className,
}: ReviewCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showHint, setShowHint] = useState(false);

  // Layers
  const layers = node.layers || {};
  const summary = layers.l1Summary as string | undefined;
  const highlights = layers.l2Highlights as string[] | undefined;

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isActive) return;
      switch (e.key) {
        case "1":
          e.preventDefault();
          onRate(node.id, "easy");
          break;
        case "2":
          e.preventDefault();
          onRate(node.id, "medium");
          break;
        case "3":
          e.preventDefault();
          onRate(node.id, "hard");
          break;
        case "4":
          e.preventDefault();
          onRate(node.id, "forgot");
          break;
      }
    },
    [isActive, node.id, onRate],
  );

  useEffect(() => {
    if (isActive) {
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }
  }, [isActive, handleKeyDown]);

  // Show summary hint after 3 seconds
  useEffect(() => {
    if (!isActive) return;
    const timer = setTimeout(() => setShowHint(true), 3000);
    return () => clearTimeout(timer);
  }, [isActive]);

  // Progress bar width
  const reviewIntervalDays = node.reviewInterval / 86400;
  const progressPercent = node.daysSinceReview != null
    ? Math.min(100, (node.daysSinceReview / reviewIntervalDays) * 100)
    : 0;

  return (
    <GlassCard
      variant={isActive ? "elevated" : "base"}
      glow={isActive ? "amber" : "none"}
      padding="lg"
      className={cn(
        "transition-all duration-300",
        isActive ? "scale-100 opacity-100" : "scale-95 opacity-50",
        className,
      )}
    >
      {/* Card counter */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-brand-amber-light" />
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">{node.title}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="brand" size="sm">
            {node.type.replace(/_/g, " ")}
          </Badge>
          <span className="text-xs text-[var(--color-text-muted)]">
            {cardIndex + 1} / {totalCards}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 rounded-full bg-[var(--color-border-subtle)] mb-4 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            progressPercent < 50
              ? "bg-semantic-success"
              : progressPercent < 80
                ? "bg-semantic-warning"
                : "bg-semantic-error",
          )}
          style={{ width: `${Math.min(100, progressPercent)}%` }}
        />
      </div>

      {/* Summary (collapsed) */}
      <div className="space-y-2">
        {/* L1 Summary */}
        {summary && !expanded && (
          <div className="text-sm text-[var(--color-text-primary)] leading-relaxed italic border-l-2 border-brand-amber/40 pl-3">
            {summary}
          </div>
        )}

        {/* Full content (expanded) */}
        {expanded && (
          <div className="space-y-3">
            <div className="text-sm text-[var(--color-text-primary)] leading-relaxed whitespace-pre-wrap">
              {node.content}
            </div>

            {/* Highlights */}
            {highlights && highlights.length > 0 && (
              <div className="space-y-1">
                <div className="text-xs text-[var(--color-text-muted)] font-semibold flex items-center gap-1">
                  <Layers className="h-3 w-3" />
                  Key points
                </div>
                <ul className="space-y-1">
                  {highlights.map((h, i) => (
                    <li key={i} className="text-sm text-[var(--color-text-secondary)] pl-3 border-l border-brand-violet/30">
                      {h}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Tags */}
            {node.tags && node.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {node.tags.map((t) => (
                  <span key={t} className="text-xs text-brand-amber-light bg-brand-amber/10 px-1.5 py-0.5 rounded">
                    {t}
                  </span>
                ))}
              </div>
            )}

            {/* Recent review history */}
            {node.recentReviews && node.recentReviews.length > 0 && (
              <div className="text-xs text-[var(--color-text-muted)]">
                <span>Recent: </span>
                {node.recentReviews.slice(0, 3).map((r, i) => (
                  <span key={i} className="ml-1">
                    {r.rating}
                    {i < Math.min(2, node.recentReviews!.length - 1) ? "," : ""}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Expand/collapse */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" />
              Show full content
            </>
          )}
        </button>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 mt-4 text-xs text-[var(--color-text-muted)]">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>{node.daysSinceReview != null ? `${node.daysSinceReview}d ago` : "Never reviewed"}</span>
        </div>
        <div className="flex items-center gap-1">
          <BarChart3 className="h-3 w-3" />
          <span>Interval: {formatInterval(node.reviewInterval)}</span>
        </div>
        <div className="flex items-center gap-1">
          <Zap className="h-3 w-3" />
          <span>{node.linksCount} links</span>
        </div>
      </div>

      {/* Rating buttons */}
      <div className="grid grid-cols-4 gap-2 mt-5">
        <AnansiButton
          variant="ghost"
          size="sm"
          onClick={() => onRate(node.id, "easy")}
          className="!text-semantic-success-light hover:!bg-semantic-success/10 !border-semantic-success/20"
        >
          1 Easy
        </AnansiButton>
        <AnansiButton
          variant="ghost"
          size="sm"
          onClick={() => onRate(node.id, "medium")}
          className="!text-brand-amber-light hover:!bg-brand-amber/10 !border-brand-amber/20"
        >
          2 Medium
        </AnansiButton>
        <AnansiButton
          variant="ghost"
          size="sm"
          onClick={() => onRate(node.id, "hard")}
          className="!text-semantic-warning-light hover:!bg-semantic-warning/10 !border-semantic-warning/20"
        >
          3 Hard
        </AnansiButton>
        <AnansiButton
          variant="ghost"
          size="sm"
          onClick={() => onRate(node.id, "forgot")}
          className="!text-semantic-error-light hover:!bg-semantic-error/10 !border-semantic-error/20"
        >
          4 Forgot
        </AnansiButton>
      </div>

      {/* Hint after 3 seconds */}
      {showHint && !expanded && (
        <div className="mt-3 text-center text-xs text-[var(--color-text-muted)] animate-pulse">
          Tip: Press 1-4 to rate · Click to expand for more context
        </div>
      )}
    </GlassCard>
  );
}
