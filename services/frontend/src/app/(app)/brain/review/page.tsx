"use client";

import { useEffect, useState, useCallback } from "react";
import { useBrainStore } from "@/stores/brain";
import { ReviewCard } from "@/components/brain/ReviewCard";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/ui/GlassCard";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";
import {
  Brain,
  RefreshCw,
  BarChart3,
  Flame,
  Star,
  Calendar,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Clock,
  Zap,
  RotateCcw,
} from "lucide-react";

interface ReviewStats {
  reviewsToday: number;
  reviewsThisWeek: number;
  totalReviews: number;
  streak: number;
  averageRating: number;
  upcomingQueueSize: number;
  ratingDistribution: Record<string, number>;
}

const RATING_KEY_MAP: Record<string, string> = {
  "1": "easy",
  "2": "medium",
  "3": "hard",
  "4": "forgot",
};

export default function BrainReviewPage() {
  const { reviewQueue, isLoadingReviewQueue, loadReviewQueue } = useBrainStore();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [isComplete, setIsComplete] = useState(false);
  const [showKeyboardHint, setShowKeyboardHint] = useState(true);

  // Load data
  useEffect(() => {
    loadReviewQueue();
    loadStats();
    const timer = setTimeout(() => setShowKeyboardHint(false), 5000);
    return () => clearTimeout(timer);
  }, [loadReviewQueue]);

  const loadStats = async () => {
    setIsLoadingStats(true);
    try {
      const resp = await api.get<{ stats: ReviewStats }>("/api/v1/brain/review/stats");
      setStats(resp.stats);
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
    setIsLoadingStats(false);
  };

  const handleRate = useCallback(
    async (nodeId: string, rating: "easy" | "medium" | "hard" | "forgot") => {
      try {
        await api.post(`/api/v1/brain/review/${nodeId}`, { rating });
        setCompletedCount((c) => c + 1);

        // Move to next card
        if (currentIndex < reviewQueue.length - 1) {
          setCurrentIndex((i) => i + 1);
        } else {
          setIsComplete(true);
        }

        // Refresh stats
        loadStats();
      } catch (err) {
        console.error("Failed to submit review:", err);
      }
    },
    [currentIndex, reviewQueue.length],
  );

  const currentItem = reviewQueue[currentIndex];
  const progress = reviewQueue.length > 0
    ? ((completedCount + currentIndex) / reviewQueue.length) * 100
    : 0;

  const handleRestart = () => {
    setCurrentIndex(0);
    setCompletedCount(0);
    setIsComplete(false);
    loadReviewQueue();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)] flex items-center gap-2">
            <RefreshCw className="h-6 w-6 text-brand-amber-light" />
            Spaced Repetition Review
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Strengthen your memory by reviewing key facts at optimal intervals
          </p>
        </div>
        <AnansiButton variant="ghost" size="sm" onClick={handleRestart}>
          <RotateCcw className="h-4 w-4" />
          Restart
        </AnansiButton>
      </div>

      <div className="grid lg:grid-cols-[1fr_280px] gap-6">
        {/* Main review area */}
        <div className="space-y-4">
          {/* Progress bar */}
          {reviewQueue.length > 0 && !isComplete && (
            <div className="flex items-center gap-3">
              <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border-subtle)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-amber to-brand-amber-light transition-all duration-500"
                  style={{ width: `${Math.min(100, progress)}%` }}
                />
              </div>
              <span className="text-xs text-[var(--color-text-muted)] shrink-0">
                {currentIndex + 1} / {reviewQueue.length}
              </span>
            </div>
          )}

          {/* Keyboard shortcut hint */}
          {showKeyboardHint && reviewQueue.length > 0 && !isComplete && (
            <div className="px-4 py-2 rounded-lg bg-brand-amber/5 border border-brand-amber/10 text-xs text-brand-amber-light text-center animate-fade-in">
              ⌨️ Keyboard shortcuts: 1=Easy · 2=Medium · 3=Hard · 4=Forgot
            </div>
          )}

          {/* Review cards */}
          {isComplete ? (
            <div className="text-center py-12">
              <div className="text-5xl mb-4">🎉</div>
              <h2 className="text-xl font-heading font-bold text-[var(--color-text-primary)] mb-2">
                Review Complete!
              </h2>
              <p className="text-[var(--color-text-muted)] mb-6">
                You reviewed {completedCount + reviewQueue.length} memories this session.
              </p>
              <AnansiButton variant="primary" onClick={handleRestart}>
                <RotateCcw className="h-4 w-4" />
                Review More
              </AnansiButton>
            </div>
          ) : isLoadingReviewQueue ? (
            <div className="space-y-4 animate-pulse">
              <div className="h-64 rounded-lg bg-white/5" />
            </div>
          ) : reviewQueue.length === 0 ? (
            <GlassCard variant="elevated" glow="amber" padding="lg" className="text-center py-12">
              <div className="text-4xl mb-3">✓</div>
              <h2 className="text-lg font-heading font-bold text-[var(--color-text-primary)] mb-2">
                All Caught Up!
              </h2>
              <p className="text-sm text-[var(--color-text-muted)] mb-4">
                No memories are due for review right now. Check back later.
              </p>
              <AnansiButton variant="secondary" onClick={loadReviewQueue}>
                <RefreshCw className="h-4 w-4" />
                Refresh
              </AnansiButton>
            </GlassCard>
          ) : (
            <div className="flex items-start justify-center">
              <ReviewCard
                key={currentItem.id}
                node={currentItem}
                onRate={handleRate}
                cardIndex={currentIndex}
                totalCards={reviewQueue.length}
                isActive={true}
                className="w-full max-w-lg"
              />
            </div>
          )}
        </div>

        {/* Stats sidebar */}
        <div className="space-y-4">
          <GlassCard variant="base" padding="md">
            <GlassCardHeader>
              <GlassCardTitle>
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-brand-teal-light" />
                  Stats
                </div>
              </GlassCardTitle>
            </GlassCardHeader>
            <GlassCardContent>
              {isLoadingStats ? (
                <div className="space-y-3 animate-pulse">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-6 rounded bg-white/5" />
                  ))}
                </div>
              ) : stats ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[var(--color-text-muted)]">Today</span>
                    <span className="text-[var(--color-text-primary)] font-semibold">
                      {stats.reviewsToday}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[var(--color-text-muted)]">This week</span>
                    <span className="text-[var(--color-text-primary)] font-semibold">
                      {stats.reviewsThisWeek}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[var(--color-text-muted)] flex items-center gap-1">
                      <Flame className="h-3.5 w-3.5 text-orange-400" />
                      Streak
                    </span>
                    <span className="text-[var(--color-text-primary)] font-semibold">
                      {stats.streak} days
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[var(--color-text-muted)] flex items-center gap-1">
                      <Star className="h-3.5 w-3.5 text-brand-amber-light" />
                      Avg rating
                    </span>
                    <span className="text-[var(--color-text-primary)] font-semibold">
                      {stats.averageRating.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[var(--color-text-muted)] flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      Queue
                    </span>
                    <span className="text-[var(--color-text-primary)] font-semibold">
                      {stats.upcomingQueueSize}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[var(--color-text-muted)]">Total</span>
                    <span className="text-[var(--color-text-primary)] font-semibold">
                      {stats.totalReviews}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-[var(--color-border-subtle)]">
                    <p className="text-xs text-[var(--color-text-muted)] mb-2">Rating distribution</p>
                    {Object.entries(stats.ratingDistribution).map(([rating, count]) => (
                      <div key={rating} className="flex items-center gap-2 text-xs mb-1">
                        <span className="capitalize w-12 text-[var(--color-text-muted)]">{rating}</span>
                        <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border-subtle)] overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              rating === "easy"
                                ? "bg-semantic-success"
                                : rating === "medium"
                                  ? "bg-brand-amber"
                                  : rating === "hard"
                                    ? "bg-semantic-warning"
                                    : "bg-semantic-error"
                            }`}
                            style={{
                              width: `${stats.totalReviews > 0 ? (count / stats.totalReviews) * 100 : 0}%`,
                            }}
                          />
                        </div>
                        <span className="text-[var(--color-text-muted)] w-6 text-right">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </GlassCardContent>
          </GlassCard>

          {/* Quick tip */}
          <GlassCard variant="base" padding="sm" glow="amber">
            <div className="flex items-start gap-2 text-xs text-[var(--color-text-muted)]">
              <Zap className="h-3.5 w-3.5 text-brand-amber-light shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-[var(--color-text-secondary)] mb-0.5">How it works</p>
                <p>
                  Rate each memory based on how well you recalled it.
                  Easy = strong recall, Forgot = need more practice.
                  Intervals adjust automatically.
                </p>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
